from pathlib import Path
import yaml
from typing import Union, Dict, List
from pydantic import BaseModel, root_validator
from jsonschema import validate
import pandas as pd

from pyam.utils import write_sheet

from nomenclature.code import Code, Tag, replace_tags
from nomenclature.error.codelist import DuplicateCodeError
from nomenclature.error.variable import (
    VariableRenameTargetError,
    VariableRenameArgError,
)


# arguments of the method `pyam.IamDataFrame.aggregate_region`
# required for checking validity of variable-CodeList-attributes
PYAM_AGG_KWARGS = [
    "components",
    "method",
    "weight",
    "drop_negative_weights",
]

here = Path(__file__).parent.absolute()


def read_validation_schema(i):
    with open(here / "validation_schemas" / f"{i}_schema.yaml", "r") as f:
        schema = yaml.safe_load(f)
    return schema


SCHEMA_TYPES = ("variable", "tag", "region", "generic")
SCHEMA_MAPPING = dict([(i, read_validation_schema(i)) for i in SCHEMA_TYPES])


class CodeList(BaseModel):
    """A class for nomenclature codelists & attributes

    Parameters
    ----------
    name : str
        Name of the CodeList
    mapping : dict, list
        Dictionary or list of Code items

    """

    name: str
    mapping: Union[List, Dict[str, Dict[str, Union[str, float, int, list, None]]]] = {}

    @root_validator()
    def cast_mapping_to_dict(cls, values):
        """Cast a mapping provided as list to a dictionary"""
        if isinstance(values["mapping"], list):
            mapping = {}

            for item in values["mapping"]:
                if not isinstance(item, Code):
                    item = Code.from_dict(item)
                if item.name in mapping:
                    raise DuplicateCodeError(name=values["name"], code=item.name)
                mapping[item.name] = item.attributes

            values["mapping"] = mapping

        return values

    @root_validator(pre=False, skip_on_failure=True)
    def check_variable_region_aggregation_args(cls, values):
        """Check that any variable "region-aggregation" mappings are valid"""
        if values["name"] == "variable":
            items = [
                (name, attrs)
                for (name, attrs) in values["mapping"].items()
                if "region-aggregation" in attrs
            ]

            for (name, attrs) in items:
                # ensure that there no pyam-aggregation-kwargs and
                conflict_args = [i for i in attrs if i in PYAM_AGG_KWARGS]
                if conflict_args:
                    raise VariableRenameArgError(
                        variable=name,
                        file=attrs["file"],
                        args=conflict_args,
                    )

                # ensure that mapped variables are defined in the nomenclature
                rename_attrs = CodeList(
                    name="region-aggregation", mapping=attrs["region-aggregation"]
                )
                invalid = [v for v in rename_attrs.keys() if v not in values["mapping"]]
                if invalid:
                    raise VariableRenameTargetError(
                        variable=name, file=attrs["file"], target=invalid
                    )
        return values

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

    @classmethod
    def from_directory(
        cls,
        name: str,
        path: Path,
        file: str = None,
    ):
        """Initialize a CodeList from a directory with codelist files

        Parameters
        ----------
        name : str
            Name of the CodeList
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        file : str, optional
            Pattern to downselect codelist files by name
        top_level_attr : str, optional
            A top-level hierarchy for codelist files with a nested structure

        Returns
        -------
        CodeList

        """
        code_list, tag_dict = [], CodeList(name="tag")
        # parse all files in path if file is None
        file = file or "**/*"

        for yaml_file in (f for f in path.glob(file) if f.suffix in {".yaml", ".yml"}):
            with open(yaml_file, "r", encoding="utf-8") as stream:
                _code_list = yaml.safe_load(stream)

            # check if this file contains a dictionary with {tag}-style keys
            if yaml_file.name.startswith("tag_"):
                # validate against the tag schema
                validate(_code_list, SCHEMA_MAPPING["tag"])

                # cast _codes to `Tag`
                for item in _code_list:
                    tag = Tag.from_dict(mapping=item)
                    tag_dict[tag.name] = [Code.from_dict(a) for a in tag.attributes]

            # if the file does not start with tag, process normally
            else:
                # validate the schema of this codelist domain (default `generic`)
                validate(
                    _code_list, SCHEMA_MAPPING.get(name, SCHEMA_MAPPING["generic"])
                )

                # a "region" codelist assumes a top-level key to be used as
                # attribute
                if name == "region":
                    _region_code_list = (
                        []
                    )  # save refactored list as new (temporary) object
                    for top_level_cat in _code_list:
                        for top_key, _codes in top_level_cat.items():
                            for item in _codes:
                                item = Code.from_dict(item)
                                item.set_attribute("hierarchy", top_key)
                                _region_code_list.append(item)
                    _code_list = _region_code_list
                else:
                    _code_list = [Code.from_dict(_dict) for _dict in _code_list]

                # add `file` attribute to each element and add to main list
                for item in _code_list:
                    item.set_attribute("file", str(yaml_file.relative_to(path.parent)))
                code_list.extend(_code_list)

        # replace tags by the items of the tag-dictionary
        for tag, tag_attrs in tag_dict.items():
            code_list = replace_tags(code_list, tag, tag_attrs)

        # iterate over the list to guard against silent replacement of duplicates
        return CodeList(name=name, mapping=code_list)

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
        source = pd.read_excel(source, sheet_name=sheet_name)

        # check for duplicates in the codelist
        duplicate_rows = source[col].duplicated(keep=False).values
        if any(duplicate_rows):
            duplicates = source[duplicate_rows]
            # set index to equal the row numbers to simplify identifying the issue
            duplicates.index = pd.Index([i + 2 for i in duplicates.index])
            msg = f"Duplicate values in the codelist:\n{duplicates.head(20)}"
            raise ValueError(msg + ("\n..." if len(duplicates) > 20 else ""))

        # set `col` as index and cast all attribute-names to lowercase
        codes = source[[col] + attrs].set_index(col)[attrs]
        codes.rename(columns={c: str(c).lower() for c in codes.columns}, inplace=True)

        return CodeList(name=name, mapping=codes.to_dict(orient="index"))

    def to_yaml(self, path=None):
        """Write mapping to yaml file or return as stream

        Parameters
        ----------
        path : :class:`pathlib.Path` or str, optional
            Write to file path if not None, otherwise return as stream
        """

        # translate to list of nested dicts, replace None by empty field, write to file
        stream = (
            yaml.dump(
                [{code: attrs} for code, attrs in self.mapping.items()], sort_keys=False
            )
            .replace(": null\n", ":\n")
            .replace(": nan\n", ":\n")
        )
        if path is not None:
            with open(path, "w") as file:
                file.write(stream)
        else:
            return stream

    def to_excel(self, excel_writer, sheet_name="definitions"):
        """Write the codelist to an Excel spreadsheet

        Parameters
        ----------
        excel_writer : str, path or ExcelWriter object
            Any valid string path, :class:`pathlib.Path` or :class:`pandas.ExcelWriter`
        sheet_name : str
            Name of sheet that will contain the codelist
        """

        # open a new ExcelWriter instance (if necessary)
        close = False
        if not isinstance(excel_writer, pd.ExcelWriter):
            close = True
            excel_writer = pd.ExcelWriter(excel_writer)

        # format and write the codelist
        codelist = (
            pd.DataFrame.from_dict(self.mapping, orient="index")
            .reset_index()
            .rename(columns={"index": self.name})
            .drop(columns="file")
        )
        codelist.rename(
            columns={c: str(c).capitalize() for c in codelist.columns}, inplace=True
        )
        write_sheet(excel_writer, sheet_name, codelist)

        # close the file if `excel_writer` arg was a file name
        if close:
            excel_writer.close()
