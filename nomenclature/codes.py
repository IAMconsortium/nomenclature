from pathlib import Path
import yaml
from typing import Dict, Optional
from pydantic import BaseModel
from jsonschema import validate

from nomenclature.codes_models import Code, Tag, replace_tags


here = Path(__file__).parent.absolute()


def read_validation_schema(i):
    with open(here / "validation_schemas" / f"{i}_schema.yaml", "r") as f:
        schema = yaml.safe_load(f)
    return schema


SCHEMA_TYPES = ("variable", "tag", "region")
SCHEMA_MAPPING = dict([(i, read_validation_schema(i)) for i in SCHEMA_TYPES])


class CodeList(BaseModel):
    """A class for nomenclature codelists & attributes"""

    name: str
    mapping: Optional[Dict] = {}

    def __setitem__(self, key, value):
        if key in self.mapping:
            raise ValueError(f"Duplicate {self.name} key: {key}")
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
    def from_directory(cls, name, path, file=None, ext=".yaml", top_level_attr=None):
        """Initialize a CodeList from a directory with codelist files

        Parameters
        ----------
        name : str
            Name of the CodeList
        path : :class:`pathlib.Path` or path-like
            Directory with the codelist files
        file : str, optional
            Pattern to downselect codelist files by name
        ext : str, optional
            Extension of the codelist files
        top_level_attr : str, optional
            A top-level hierarchy for codelist files with a nested structure

        Returns
        -------
        CodeList

        """
        code_list, tag_dict = [], CodeList(name="tag")

        # parse all files in path if file is None
        file = file or "**/*"

        # parse all files
        for f in path.glob(f"{file}{ext}"):
            with open(f, "r", encoding="utf-8") as stream:
                _code_list = yaml.safe_load(stream)

            # check if this file contains a dictionary with <tag>-style keys
            if f.name.startswith("tag_"):
                # validate against the tag schema
                validate(_code_list, SCHEMA_MAPPING["tag"])

                # cast _codes to `Tag`
                for item in _code_list:
                    tag = Tag.from_dict(mapping=item)
                    tag_dict[tag.name] = [Code.from_dict(a) for a in tag.attributes]
                continue

            # validate against the schema of this codelist domain
            validate(_code_list, SCHEMA_MAPPING[name])

            # if specified, set top-level key as attribute instead
            if top_level_attr is not None:
                original_code_list, _code_list = _code_list.copy(), []
                for top_level_cat in original_code_list:
                    for top_key, _codes in top_level_cat.items():
                        for item in _codes:
                            item = Code.from_dict(item)
                            item.set_attribute(top_level_attr, top_key)
                            _code_list.append(item)
            else:
                _code_list = [Code.from_dict(_dict) for _dict in _code_list]

            # add `file` attribute to each element and add to main list
            for item in _code_list:
                item.set_attribute("file", str(f))
            code_list.extend(_code_list)

        # replace tags by the items of the tag-dictionary
        for tag, tag_attrs in tag_dict.items():
            code_list = replace_tags(code_list, tag, tag_attrs)

        # iterate over the list to guard against silent replacement of duplicates
        cl = CodeList(name=name)
        for item in code_list:
            cl[item.name] = item.attributes

        return cl
