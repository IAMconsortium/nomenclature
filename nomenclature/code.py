from typing import Union, List, Dict, Optional, ClassVar
from pydantic import BaseModel, StrictStr, StrictInt, StrictFloat, StrictBool


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    description: Optional[str]
    attributes: Union[
        Dict[
            str,
            Union[StrictStr, StrictInt, StrictFloat, StrictBool, List, None, Dict[
                str, Union[StrictStr, StrictInt, StrictFloat, StrictBool, List, None]
                ]

            ]
        ],
        List[StrictStr],
    ]

    @classmethod
    def from_dict(cls, mapping):
        if isinstance(mapping, str):
            return cls(name=mapping, attributes={})

        if len(mapping) != 1:
            raise ValueError(f"Code is not a single name-attributes mapping: {mapping}")

        attributes = list(mapping.values())[0]

        description = None
        for de in ["definition", "description"]:
            if de in attributes:
                description = attributes[de]
                del attributes[de]

        return cls(
            name=list(mapping.keys())[0],
            description=description,
            attributes=attributes,
        )

    def set_attribute(self, key, value):
        self.attributes[key] = value

    @classmethod
    def replace_tags(cls, code_list, tag, tag_dict):
        """Replace tags in `code_list` by `tag_dict`"""

        _code_list = []

        for code in code_list:
            if f"{{{tag}}}" in code.name:
                _code_list.extend(cls._replace_tags(code, tag, tag_dict))
            else:
                _code_list.append(code)

        return _code_list

    @classmethod
    def _replace_tags(cls, code, tag, target_list):
        """Utility implementation to replace tags in each item and update attributes"""

        _code_list = []

        for target in target_list:
            key = code.name.replace(f"{{{tag}}}", target.name)
            desc = code.description.replace(f"{{{tag}}}", target.description)
            attrs = code.attributes.copy()
            for _key, _value in target.attributes.items():
                if _key in attrs:
                    attrs[_key] = attrs[_key].replace(f"{{{tag}}}", _value)

            _code = Code(name=key, description=desc, attributes=attrs)
            _code_list.append(_code)

        return _code_list


class Tag(Code):
    """A simple class for a mapping of a "{tag}" to "target codes" and attributes"""

    attributes: List[
        Dict[str, Union[str, Dict[str, Union[str, int, float, bool, List, None]], None]]
    ]


class VariableCode(Code):

    unit: Optional[str]
    weight: Optional[str]
    region_aggregation: Optional[List[Dict[str, Dict]]]
    skip_region_aggregation: Optional[bool]
    method: Optional[str]
    check_aggregate: Optional[bool]
    components: Optional[Union[List[str], List[Dict[str, List[str]]]]]

    EXPECTED_ATTR: ClassVar[List] = [
        "unit",
        "weight",
        "region-aggregation",
        "skip-region-aggregation",
        "method",
        "check-aggregate",
        "components",
    ]

    @classmethod
    def from_dict(cls, mapping):
        inst = Code.from_dict(mapping)

        if "unit" not in inst.attributes:
            raise ValueError(f"Unit not defined for variable {inst.name}")

        found_attr = {}
        for code in cls.EXPECTED_ATTR:
            if code in inst.attributes:
                found_attr[code] = inst.attributes[code]
                del inst.attributes[code]

        return cls(
            name=inst.name,
            description=inst.description,
            attributes=inst.attributes,
            unit=found_attr["unit"],
            weight=found_attr.get("weight", None),
            region_aggregation=found_attr.get("region-aggregation", None),
            skip_region_aggregation=found_attr.get("skip-region-aggregation", None),
            method=found_attr.get("method", None),
            check_aggregate=found_attr.get("check-aggregate", None),
            components=found_attr.get("components", None),
        )

    @classmethod
    def _replace_tags(cls, code, tag, target_list):
        """Utility implementation to replace tags in each item and update attributes"""

        _code_list = []

        for target in target_list:
            key = code.name.replace(f"{{{tag}}}", target.name)
            desc = code.description.replace(f"{{{tag}}}", target.description)
            attrs = code.attributes.copy()
            for _key, _value in target.attributes.items():
                if _key in attrs:
                    attrs[_key] = attrs[_key].replace(f"{{{tag}}}", _value)

            code_dict = code.dict()

            for attr, val in code.dict().items():
                if attr in target.attributes:
                    code_dict[attr] = val.replace(f"{{{tag}}}", target.attributes[attr])

            _code = cls(
                name=key,
                description=desc,
                attributes=attrs,
                unit=code_dict["unit"],
                weight=code_dict["weight"],
                region_aggregation=code_dict["region_aggregation"],
                skip_region_aggregation=code_dict["skip_region_aggregation"],
                method=code_dict["method"],
                check_aggregate=code_dict["check_aggregate"],
                components=code_dict["components"],
            )
            _code_list.append(_code)

        return _code_list
