from pathlib import Path
from typing import ClassVar, Dict, List

import pandas as pd
import numpy as np
import yaml
import logging
from jsonschema import validate
from pyam.utils import write_sheet
from pydantic import BaseModel, validator

from nomenclature.code import Code, VariableCode, RegionCode
from nomenclature.error.codelist import DuplicateCodeError
from nomenclature.error.variable import (
    MissingWeightError,
    VariableRenameArgError,
    VariableRenameTargetError,
)


here = Path(__file__).parent.absolute()


def read_validation_schema(i):
    with open(here / "validation_schemas" / f"{i}_schema.yaml", "r") as f:
        schema = yaml.safe_load(f)
    return schema


SCHEMA_TYPES = ("variable", "tag", "region", "generic")
SCHEMA_MAPPING = dict([(i, read_validation_schema(i)) for i in SCHEMA_TYPES])


class CodeList(BaseModel):
    """A class for nomenclature codelists & attributes

    Attributes
    ----------
    name : str
        Name of the CodeList
    mapping : dict
        Dictionary of `Code` objects

    """

    name: str
    mapping: Dict[str, Code] = {}

    # class variable
    validation_schema: ClassVar[str] = "generic"
    code_basis: ClassVar = Code

    @validator("mapping")
    def check_stray_tag(cls, v):
        """Check that no '{' are left in codes after tag replacement"""
        for code in v:
            if "{" in code:
                raise ValueError(
                    f"Unexpected {{}} in codelist: {code}."
                    " Check if the tag was spelled correctly."
                )
        return v

    @validator("mapping")
    def check_end_whitespace(cls, v, values):
        """Check that no code ends with a whitespace"""
        for code in v:
            if code.endswith(" "):
                raise ValueError(
                    f"Unexpected whitespace at the end of a {values['name']}"
                    f" code: '{code}'."
                )
        return v

    def __setitem__(self, key, value):
        if key in self.mapping:
            raise DuplicateCodeError(name=self.name, code=key)
        self.mapping[key] = value

    def __getitem__(self, k):
        return self.mapping[k]

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __repr__(self):
        return self.mapping.__repr__()

    def items(self):
        return self.mapping.items()

    def keys(self):
        return self.mapping.keys()

    def values(self):
        return self.mapping.values()

    def validate_items(self, items: List[str]) -> List[str]:
        """Validate that a list of items are valid codes

        Returns
        -------
        list
            Returns the list of items that are **not** defined in the codelist
        """
        return [c for c in items if c not in self.keys()]

    @classmethod
    def replace_tags(
        cls, code_list: List[Code], tag_name: str, tags: List[Code]
    ) -> List[Code]:
        _code_list: List[Code] = []

        for code in code_list:
            if "{" + tag_name + "}" in code.name:
                _code_list.extend((code.replace_tag(tag_name, tag) for tag in tags))
            else:
                _code_list.append(code)

        return _code_list

    @classmethod
    def _parse_and_replace_tags(
        cls,
        code_list: List[Code],
        path: Path,
        file_glob_pattern: str = "**/*",
    ) -> List[Code]:
        """Cast, validate and replace tags into list of codes for one dimension

        Parameters
        ----------
        code_list : List[Code]
            List of Code to modify
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        file_glob_pattern : str, optional
            Pattern to downselect codelist files by name, default: "**/*" (i.e. all
            files in all sub-folders)

        Returns
        -------
        Dict[str, Code] :class: `nomenclature.Code`

        """
        tag_dict: Dict[str, List[Code]] = {}

        for yaml_file in (
            f
            for f in path.glob(file_glob_pattern)
            if f.suffix in {".yaml", ".yml"} and f.name.startswith("tag_")
        ):
            with open(yaml_file, "r", encoding="utf-8") as stream:
                _tag_list = yaml.safe_load(stream)

            # validate against the tag schema
            validate(_tag_list, SCHEMA_MAPPING["tag"])

            for tag in _tag_list:
                tag_name = next(iter(tag))
                if tag_name in tag_dict:
                    raise DuplicateCodeError(name="tag", code=tag_name)
                tag_dict[tag_name] = [Code.from_dict(t) for t in tag[tag_name]]

        # start with all non tag codes
        codes_without_tags = [code for code in code_list if not code.contains_tags]
        codes_with_tags = [code for code in code_list if code.contains_tags]

        # replace tags by the items of the tag-dictionary
        for tag_name, tags in tag_dict.items():
            codes_with_tags = cls.replace_tags(codes_with_tags, tag_name, tags)

        return codes_without_tags + codes_with_tags

    @classmethod
    def from_directory(cls, name: str, path: Path, file_glob_pattern: str = "**/*"):
        """Initialize a CodeList from a directory with codelist files

        Parameters
        ----------
        name : str
            Name of the CodeList
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        file_glob_pattern : str, optional
            Pattern to downselect codelist files by name

        Returns
        -------
        instance of cls (CodeList if not inherited)

        """
        code_list: List[Code] = []

        for yaml_file in (
            f
            for f in path.glob(file_glob_pattern)
            if f.suffix in {".yaml", ".yml"} and not f.name.startswith("tag_")
        ):
            with open(yaml_file, "r", encoding="utf-8") as stream:
                _code_list = yaml.safe_load(stream)

            # validate the schema of this codelist domain (default `generic`)
            validate(_code_list, SCHEMA_MAPPING[cls.validation_schema])

            for code_dict in _code_list:
                code = cls.code_basis.from_dict(code_dict)
                # add `file` attribute
                code.file = yaml_file.relative_to(path.parent).as_posix()
                code_list.append(code)
        code_list = cls._parse_and_replace_tags(code_list, path, file_glob_pattern)
        mapping: Dict[str, Code] = {}
        for code in code_list:
            if code.name in mapping:
                raise DuplicateCodeError(name=name, code=code.name)
            mapping[code.name] = code
        return cls(name=name, mapping=mapping)

    @classmethod
    def read_excel(cls, name, source, sheet_name, col, attrs=[]):
        """Parses an xlsx file with a codelist

        Parameters
        ----------
        name : str
            Name of the CodeList
        source : str, path, file-like object
            Path to Excel file with definitions (codelists).
        sheet_name : str
            Sheet name of `source`.
        col : str
            Column from `sheet_name` to use as codes.
        attrs : list, optional
            Columns from `sheet_name` to use as attributes.
        """
        codelist = pd.read_excel(source, sheet_name=sheet_name, usecols=[col] + attrs)

        # replace nan with None
        codelist = codelist.replace(np.nan, None)

        # check for duplicates in the codelist
        duplicate_rows = codelist[col].duplicated(keep=False).values
        if any(duplicate_rows):
            duplicates = codelist[duplicate_rows]
            # set index to equal the row numbers to simplify identifying the issue
            duplicates.index = pd.Index([i + 2 for i in duplicates.index])
            msg = f"Duplicate values in the codelist:\n{duplicates.head(20)}"
            raise ValueError(msg + ("\n..." if len(duplicates) > 20 else ""))

        # set `col` as index and cast all attribute-names to lowercase
        codes = codelist[[col] + attrs].set_index(col)[attrs]
        codes.rename(columns={c: str(c).lower() for c in codes.columns}, inplace=True)
        codes_di = codes.to_dict(orient="index")
        mapp = {
            title: cls.code_basis.from_dict({title: values})
            for title, values in codes_di.items()
        }

        return cls(name=name, mapping=mapp)

    def to_yaml(self, path=None):
        """Write mapping to yaml file or return as stream

        Parameters
        ----------
        path : :class:`pathlib.Path` or str, optional
            Write to file path if not None, otherwise return as stream
        """

        class Dumper(yaml.Dumper):
            def increase_indent(self, flow=False, *args, **kwargs):
                return super().increase_indent(flow=flow, indentless=False)

        # translate to list of nested dicts, replace None by empty field, write to file
        stream = (
            yaml.dump(
                [{code: attrs} for code, attrs in self.codelist_repr().items()],
                sort_keys=False,
                Dumper=Dumper,
            )
            .replace(": null\n", ":\n")
            .replace(": nan\n", ":\n")
        )

        if path is not None:
            with open(path, "w") as file:
                file.write(stream)
        else:
            return stream

    def to_pandas(self, sort_by_code: bool = False) -> pd.DataFrame:
        """Export the CodeList to a :class:`pandas.DataFrame`

        Parameters
        ----------
        sort_by_code : bool, optional
            Sort the codelist before exporting to csv.
        """
        codelist = (
            pd.DataFrame.from_dict(
                self.codelist_repr(json_serialized=True), orient="index"
            )
            .reset_index()
            .rename(columns={"index": self.name})
            .drop(columns="file")
        )
        if sort_by_code:
            codelist.sort_values(by=self.name, inplace=True)
        codelist.rename(
            columns={c: str(c).capitalize() for c in codelist.columns}, inplace=True
        )
        return codelist

    def to_csv(self, path=None, sort_by_code: bool = False, **kwargs):
        """Write the codelist to a comma-separated values (csv) file

        Parameters
        ----------
        path : str, path or file-like, optional
            File path as string or :class:`pathlib.Path`, or file-like object.
            If *None*, the result is returned as a csv-formatted string.
            See :meth:`pandas.DataFrame.to_csv` for details.
        sort_by_code : bool, optional
            Sort the codelist before exporting to csv.
        **kwargs
            Passed to :meth:`pandas.DataFrame.to_csv`.

        Returns
        -------
        None or csv-formatted string (if *path* is None)
        """
        index = kwargs.pop("index", False)  # by default, do not write index to csv
        return self.to_pandas(sort_by_code).to_csv(path, index=index, **kwargs)

    def to_excel(
        self, excel_writer, sheet_name=None, sort_by_code: bool = False, **kwargs
    ):
        """Write the codelist to an Excel spreadsheet

        Parameters
        ----------
        excel_writer : path-like, file-like, or ExcelWriter object
            File path as string or :class:`pathlib.Path`,
            or existing :class:`pandas.ExcelWriter`.
        sheet_name : str, optional
            Name of sheet that will have the codelist. If *None*, use the codelist name.
        sort_by_code : bool, optional
            Sort the codelist before exporting to file.
        **kwargs
            Passed to :class:`pandas.ExcelWriter` (if *excel_writer* is path-like).
        """

        # default sheet_name to the name of the codelist
        if sheet_name is None:
            sheet_name = self.name

        # open a new ExcelWriter instance (if necessary)
        close = False
        if not isinstance(excel_writer, pd.ExcelWriter):
            close = True
            excel_writer = pd.ExcelWriter(excel_writer, **kwargs)

        write_sheet(excel_writer, sheet_name, self.to_pandas(sort_by_code))

        # close the file if `excel_writer` arg was a file name
        if close:
            excel_writer.close()

    def codelist_repr(self, json_serialized=False) -> Dict:
        """Cast a CodeList into corresponding dictionary"""

        nice_dict = {}
        for name, code in self.mapping.items():
            code_dict = (
                code.flattened_dict_serialized
                if json_serialized
                else code.flattened_dict
            )
            code_dict = {
                k: v
                for k, v in code_dict.items()
                if (v is not None and k != "name") or k == "unit"
            }

            nice_dict[name] = code_dict

        return nice_dict

    def filter(self, **kwargs) -> "CodeList":
        """Filter a CodeList by any attribute-value pairs.

        Parameters
        ----------
        **kwargs
            Attribute-value mappings to be used for filtering.

        Returns
        -------
        CodeList
            CodeList with Codes that match attribute-value pairs.
        """

        # Returns True if code satisfies all filter parameters
        def _match_attribute(code, kwargs):
            return all(
                hasattr(code, attribute) and getattr(code, attribute, None) == value
                for attribute, value in kwargs.items()
            )

        filtered_codelist = CodeList(
            name=self.name,
            mapping={
                code.name: code
                for code in self.mapping.values()
                if _match_attribute(code, kwargs)
            },
        )

        if not filtered_codelist.mapping:
            logging.warning("Formatted data is empty!")
        return filtered_codelist


class VariableCodeList(CodeList):
    """A subclass of CodeList specified for variables

    Attributes
    ----------
    name : str
        Name of the VariableCodeList
    mapping : dict
        Dictionary of `VariableCode` objects

    """

    # class variables
    code_basis: ClassVar = VariableCode
    validation_schema: ClassVar[str] = "variable"

    @validator("mapping")
    def check_variable_region_aggregation_args(cls, v):
        """Check that any variable "region-aggregation" mappings are valid"""

        for var in v.values():
            # ensure that a variable does not have both individual
            # pyam-aggregation-kwargs and a 'region-aggregation' attribute
            if var.region_aggregation is not None:
                if conflict_args := list(var.pyam_agg_kwargs.keys()):
                    raise VariableRenameArgError(
                        variable=var.name,
                        file=var.file,
                        args=conflict_args,
                    )

                # ensure that mapped variables are defined in the nomenclature
                invalid = []
                for inst in var.region_aggregation:
                    invalid.extend(var for var in inst if var not in v)
                if invalid:
                    raise VariableRenameTargetError(
                        variable=var.name, file=var.file, target=invalid
                    )
        return v

    @validator("mapping")
    def check_weight_in_vars(cls, v):
        """Check that all variables specified in 'weight' are present in the codelist"""
        if missing_weights := [
            (var.name, var.weight, var.file)
            for var in v.values()
            if var.weight is not None and var.weight not in v
        ]:
            raise MissingWeightError(
                missing_weights="".join(
                    f"'{weight}' used for '{var}' in: {file}\n"
                    for var, weight, file in missing_weights
                )
            )
        return v

    @validator("mapping")
    def cast_variable_components_args(cls, v):
        """Cast "components" list of dicts to a codelist"""

        # translate a list of single-key dictionaries to a simple dictionary
        for var in v.values():
            if var.components and isinstance(var.components[0], dict):
                comp = {}
                for val in var.components:
                    comp.update(val)
                v[var.name].components = comp

        return v

    def vars_default_args(self, variables: List[str]) -> List[VariableCode]:
        """return subset of variables which does not feature any special pyam
        aggregation arguments and where skip_region_aggregation is False"""
        return [
            self[var]
            for var in variables
            if not self[var].agg_kwargs and not self[var].skip_region_aggregation
        ]

    def vars_kwargs(self, variables: List[str]) -> List[VariableCode]:
        # return subset of variables which features special pyam aggregation arguments
        # and where skip_region_aggregation is False
        return [
            self[var]
            for var in variables
            if self[var].agg_kwargs and not self[var].skip_region_aggregation
        ]


class RegionCodeList(CodeList):
    """A subclass of CodeList specified for regions

    Attributes
    ----------
    name : str
        Name of the RegionCodeList
    mapping : dict
        Dictionary of `RegionCode` objects

    """

    # class variable
    code_basis: ClassVar = RegionCode
    validation_schema: ClassVar[str] = "region"

    @classmethod
    def from_directory(cls, name: str, path: Path, file_glob_pattern: str = "**/*"):
        """Initialize a RegionCodeList from a directory with codelist files

        Parameters
        ----------
        name : str
            Name of the CodeList
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        file_glob_pattern : str, optional
            Pattern to downselect codelist files by name, default: "**/*" (i.e. all
            files in all sub-folders)

        Returns
        -------
        RegionCodeList

        """
        mapping: Dict[str, RegionCode] = {}
        code_list: List[RegionCode] = []

        for yaml_file in (
            f
            for f in path.glob(file_glob_pattern)
            if f.suffix in {".yaml", ".yml"} and not f.name.startswith("tag_")
        ):
            with open(yaml_file, "r", encoding="utf-8") as stream:
                _code_list = yaml.safe_load(stream)

            # a "region" codelist assumes a top-level category to be used as attribute
            for top_level_cat in _code_list:
                for top_key, _codes in top_level_cat.items():
                    for item in _codes:
                        code = RegionCode.from_dict(item)
                        code.hierarchy = top_key
                        code.file = yaml_file.relative_to(path.parent).as_posix()
                        code_list.append(code)

        code_list = cls._parse_and_replace_tags(code_list, path, file_glob_pattern)

        mapping: Dict[str, RegionCode] = {}
        for code in code_list:
            if code.name in mapping:
                raise DuplicateCodeError(name=name, code=code.name)
            mapping[code.name] = code

        return cls(name=name, mapping=mapping)

    @property
    def hierarchy(self) -> List[str]:
        """Return the hierarchies defined in the RegionCodeList

        Returns
        -------
        List[str]

        """
        return sorted(list(set(v.hierarchy for v in self.mapping.values())))

    def filter(self, hierarchy: str) -> "RegionCodeList":
        """Return a filtered RegionCodeList object

        Parameters
        ----------
        hierarchy : str
            String with filter parameter.

        Raises
        ------
        ValueError
            Provided hierarchy is not compatible with the given model.

        Returns
        -------
        :class:'RegionCodeList'

        Notes
        -----
        The following arguments are available for filtering:

        - 'hierarchy': filter by the hierarchy of each region

        """

        mapping = {k: v for k, v in self.mapping.items() if v.hierarchy == hierarchy}
        if mapping:
            return RegionCodeList(name=self.name, mapping=mapping)
        else:
            msg: str = (
                f"Filtered RegionCodeList is empty: hierarchy={hierarchy}\n"
                "Use `RegionCodeList.hierarchy` method for available items."
            )
            raise ValueError(msg)
