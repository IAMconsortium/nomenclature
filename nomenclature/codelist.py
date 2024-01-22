from contextlib import suppress
import logging
from pathlib import Path
from typing import ClassVar, Dict, List

import numpy as np
import pandas as pd
import yaml
from pyam.utils import write_sheet
from pydantic import field_validator, BaseModel, ValidationInfo
from pydantic_core import PydanticCustomError

import nomenclature
from nomenclature.code import Code, MetaCode, RegionCode, VariableCode
from nomenclature.config import NomenclatureConfig
from nomenclature.error import custom_pydantic_errors, ErrorCollector
from pyam.utils import is_list_like

here = Path(__file__).parent.absolute()


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

    def __eq__(self, other):
        return self.name == other.name and self.mapping == other.mapping

    @field_validator("mapping")
    @classmethod
    def check_stray_tag(cls, v: Dict[str, Code]) -> Dict[str, Code]:
        """Check that no '{' are left in codes after tag replacement"""
        for code in v:
            if "{" in code:
                raise ValueError(
                    f"Unexpected {{}} in codelist: {code}."
                    " Check if the tag was spelled correctly."
                )
        return v

    @field_validator("mapping")
    @classmethod
    def check_end_whitespace(
        cls, v: Dict[str, Code], info: ValidationInfo
    ) -> Dict[str, Code]:
        """Check that no code ends with a whitespace"""
        for code in v:
            if code.endswith(" "):
                raise ValueError(
                    f"Unexpected whitespace at the end of a {info.data['name']}"
                    f" code: '{code}'."
                )
        return v

    def __setitem__(self, key: str, value: Code) -> None:
        if key in self.mapping:
            raise ValueError(f"Duplicate item in {self.name} codelist: {key}")
        if not isinstance(value, Code):
            raise TypeError("Codelist can only contain Code items")
        if key != value.name:
            raise ValueError("Key has to be equal to code name")
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

            for tag in _tag_list:
                tag_name = next(iter(tag))
                if tag_name in tag_dict:
                    raise ValueError(f"Duplicate item in tag codelist: {tag_name}")
                tag_dict[tag_name] = [Code.from_dict(t) for t in tag[tag_name]]

        # start with all non tag codes
        codes_without_tags = [code for code in code_list if not code.contains_tags]
        codes_with_tags = [code for code in code_list if code.contains_tags]

        # replace tags by the items of the tag-dictionary
        for tag_name, tags in tag_dict.items():
            codes_with_tags = cls.replace_tags(codes_with_tags, tag_name, tags)

        return codes_without_tags + codes_with_tags

    @classmethod
    def from_directory(
        cls,
        name: str,
        path: Path,
        config: NomenclatureConfig = None,
        file_glob_pattern: str = "**/*",
    ):
        """Initialize a CodeList from a directory with codelist files

        Parameters
        ----------
        name : str
            Name of the CodeList
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        config: :class:`NomenclatureConfig`, optional
            Attributes for configuring the CodeList
        file_glob_pattern : str, optional
            Pattern to downselect codelist files by name

        Returns
        -------
        instance of cls (:class:`CodeList` if not inherited)

        """
        code_list = cls._parse_codelist_dir(path, file_glob_pattern)

        with suppress(AttributeError):
            dimension = path.name
            codelistconfig = getattr(config.definitions, dimension)
            for repo in codelistconfig.repositories:
                repo_path = (
                    config.repositories[repo].local_path / "definitions" / dimension
                )
                code_list = (
                    cls._parse_codelist_dir(
                        repo_path,
                        file_glob_pattern,
                    )
                    + code_list
                )
        errors = ErrorCollector()
        mapping: Dict[str, Code] = {}
        for code in code_list:
            if code.name in mapping:
                errors.append(
                    ValueError(f"Duplicate item in {name} codelist: {code.name}")
                )
            mapping[code.name] = code
        if errors:
            raise ValueError(errors)
        return cls(name=name, mapping=mapping)

    @classmethod
    def _parse_codelist_dir(cls, path: Path, file_glob_pattern: str = "**/*"):
        code_list: List[Code] = []
        for yaml_file in (
            f
            for f in path.glob(file_glob_pattern)
            if f.suffix in {".yaml", ".yml"} and not f.name.startswith("tag_")
        ):
            with open(yaml_file, "r", encoding="utf-8") as stream:
                _code_list = yaml.safe_load(stream)
            for code_dict in _code_list:
                code = cls.code_basis.from_dict(code_dict)
                code.file = yaml_file.relative_to(path.parent).as_posix()
                code_list.append(code)

        code_list = cls._parse_and_replace_tags(code_list, path, file_glob_pattern)
        return code_list

    @classmethod
    def read_excel(cls, name, source, sheet_name, col, attrs=None):
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
        if attrs is None:
            attrs = []
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
            def increase_indent(self, flow: bool = False, indentless: bool = False):
                return super().increase_indent(flow=flow, indentless=indentless)

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

        if path is None:
            return stream
        with open(path, "w") as file:
            file.write(stream)

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
            nice_dict[name] = {k: v for k, v in code_dict.items() if k != "name"}

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
                hasattr(code, attribute) and getattr(code, attribute) == value
                for attribute, value in kwargs.items()
            )

        filtered_codelist = self.__class__(
            name=self.name,
            mapping={
                code.name: code
                for code in self.mapping.values()
                if _match_attribute(code, kwargs)
            },
        )

        if not filtered_codelist.mapping:
            logging.warning(f"Filtered {self.__class__.__name__} is empty!")
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

    @property
    def units(self):
        """Get the list of all units"""
        units = set()

        # replace "dimensionless" variables (unit: `None`) with empty string
        # for consistency with the yaml file format
        def to_dimensionless(u):
            return u or ""

        for variable in self.mapping.values():
            if is_list_like(variable.unit):
                units.update([to_dimensionless(u) for u in variable.unit])
            else:
                units.add(to_dimensionless(variable.unit))

        return sorted(list(units))

    @field_validator("mapping")
    @classmethod
    def check_variable_region_aggregation_args(cls, v):
        """Check that any variable "region-aggregation" mappings are valid"""

        for var in v.values():
            # ensure that a variable does not have both individual
            # pyam-aggregation-kwargs and a 'region-aggregation' attribute
            if var.region_aggregation is not None:
                if conflict_args := list(var.pyam_agg_kwargs.keys()):
                    raise PydanticCustomError(
                        *custom_pydantic_errors.VariableRenameArgError,
                        {"variable": var.name, "file": var.file, "args": conflict_args},
                    )

                # ensure that mapped variables are defined in the nomenclature
                invalid = []
                for inst in var.region_aggregation:
                    invalid.extend(var for var in inst if var not in v)
                if invalid:
                    raise PydanticCustomError(
                        *custom_pydantic_errors.VariableRenameTargetError,
                        {"variable": var.name, "file": var.file, "target": invalid},
                    )
        return v

    @field_validator("mapping")
    @classmethod
    def check_weight_in_vars(cls, v):
        """Check that all variables specified in 'weight' are present in the codelist"""
        if missing_weights := [
            (var.name, var.weight, var.file)
            for var in v.values()
            if var.weight is not None and var.weight not in v
        ]:
            raise PydanticCustomError(
                *custom_pydantic_errors.MissingWeightError,
                {
                    "missing_weights": "".join(
                        f"'{weight}' used for '{var}' in: {file}\n"
                        for var, weight, file in missing_weights
                    )
                },
            )
        return v

    @field_validator("mapping")
    @classmethod
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
    def from_directory(
        cls,
        name: str,
        path: Path,
        config: NomenclatureConfig = None,
        file_glob_pattern: str = "**/*",
    ):
        """Initialize a RegionCodeList from a directory with codelist files

        Parameters
        ----------
        name : str
            Name of the CodeList
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        config : :class:`RegionCodeListConfig`, optional
            Attributes for configuring the CodeList
        file_glob_pattern : str, optional
            Pattern to downselect codelist files by name, default: "**/*" (i.e. all
            files in all sub-folders)

        Returns
        -------
        RegionCodeList

        """

        code_list: List[RegionCode] = []

        # initializing from general configuration
        with suppress(AttributeError):
            # adding all countries
            if config.definitions.region.country is True:
                for c in nomenclature.countries:
                    try:
                        code_list.append(
                            RegionCode(
                                name=c.name, iso3_codes=c.alpha_3, hierarchy="Country"
                            )
                        )
                    # special handling for countries that do not have an alpha_3 code
                    except AttributeError:
                        code_list.append(RegionCode(name=c.name, hierarchy="Country"))

            # importing from an external repository
            for repo in config.definitions.region.repositories:
                repo_path = (
                    config.repositories[repo].local_path / "definitions" / "region"
                )

                code_list = cls._parse_region_code_dir(
                    code_list,
                    repo_path,
                    file_glob_pattern,
                    repository=config.definitions.region.repositories,
                )
                code_list = cls._parse_and_replace_tags(
                    code_list, repo_path, file_glob_pattern
                )

        # parse from current repository
        code_list = cls._parse_region_code_dir(code_list, path, file_glob_pattern)
        code_list = cls._parse_and_replace_tags(code_list, path, file_glob_pattern)

        # translate to mapping
        mapping: Dict[str, RegionCode] = {}

        errors = ErrorCollector()
        for code in code_list:
            if code.name in mapping:
                errors.append(ValueError(f"Trying to set a duplicate code {code.name}"))
            mapping[code.name] = code
        if errors:
            raise ValueError(errors)
        return cls(name=name, mapping=mapping)

    @property
    def hierarchy(self) -> List[str]:
        """Return the hierarchies defined in the RegionCodeList

        Returns
        -------
        List[str]

        """
        return sorted(list({v.hierarchy for v in self.mapping.values()}))

    @classmethod
    def _parse_region_code_dir(
        cls,
        code_list: List[Code],
        path: Path,
        file_glob_pattern: str = "**/*",
        repository: Path = None,
    ) -> List[RegionCode]:
        """"""

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
                        if repository:
                            code.repository = repository
                        code.file = yaml_file.relative_to(path.parent).as_posix()
                        code_list.append(code)

        return code_list


class MetaCodeList(CodeList):
    """A subclass of CodeList specified for MetaCodes

    Attributes
    ----------
    name : str
        Name of the MetaCodeList
    mapping : dict
        Dictionary of `MetaCode` objects

    """

    code_basis: ClassVar = MetaCode
    validation_schema: ClassVar[str] = "generic"
