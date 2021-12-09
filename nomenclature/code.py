from re import compile, match
from typing import Union, List, Dict
from pydantic import BaseModel, validator


TAG_PATTERN = compile("^<.*>$")


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    attributes: Dict[str, Union[str, int, float, bool, List, None]]

    @classmethod
    def from_dict(cls, mapping):
        if isinstance(mapping, str):
            return cls(name=mapping, attributes={})

        if len(mapping) != 1:
            raise ValueError(f"Code is not a single name-attributes mapping: {mapping}")

        return cls(name=list(mapping.keys())[0], attributes=list(mapping.values())[0])

    def set_attribute(self, key, value):
        self.attributes[key] = value


class Tag(Code):
    """A simple class for a mapping of a "<tag>" to "target codes" and attributes"""

    attributes: List[
        Dict[str, Union[str, Dict[str, Union[str, int, float, bool, List, None]], None]]
    ]

    @validator("name")
    def validate_tag_format(cls, v):
        # Note: the pattern is also enforced by json-schema via the tag_schema.yaml
        if not match(TAG_PATTERN, v):
            raise ValueError(f"The key is not formatted as a tag (`<..>`): {v}")
        return v


def replace_tags(code_list, tag, tag_dict):
    """Replace tags in `code_list` by `tag_dict`"""

    _code_list = []

    for code in code_list:
        if tag in code.name:
            _code_list.extend(_replace_tags(code, tag, tag_dict))
        else:
            _code_list.append(code)

    return _code_list


def _replace_tags(code, tag, target_list):
    """Utility implementation to replace tags in each item and update attributes"""

    _code_list = []

    for target in target_list:
        key = code.name.replace(tag, target.name)
        attrs = code.attributes.copy()
        for _key, _value in target.attributes.items():
            if _key in attrs:
                attrs[_key] = attrs[_key].replace(tag, _value)

        _code = Code(name=key, attributes=attrs)
        _code_list.append(_code)

    return _code_list
