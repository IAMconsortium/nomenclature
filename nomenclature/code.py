import re
from typing import Union, List, Dict, Optional
from pydantic import BaseModel, StrictStr, StrictInt, StrictFloat, StrictBool


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    description: Optional[str]
    attributes: Union[
        Dict[
            str,
            Union[
                StrictStr,
                StrictInt,
                StrictFloat,
                StrictBool,
                List,
                None,
                Dict[
                    str,
                    Union[StrictStr, StrictInt, StrictFloat, StrictBool, List, None],
                ],
            ],
        ],
        List[StrictStr],
    ]

    @classmethod
    def from_dict(cls, mapping):
        if isinstance(mapping, str):
            return cls(name=mapping, attributes={})

        if len(mapping) != 1:
            raise ValueError(f"Code is not a single name-attributes mapping: {mapping}")

        # extract the name of the code
        name = list(mapping.keys())[0]
        # overwrite the mapping as just the code content
        mapping = mapping[name]

        # check if we have a "definition" attribute and map it to "description"
        if "definition" in mapping:
            if "description" not in mapping:
                mapping["description"] = mapping["definition"]
                del mapping["definition"]
            else:
                raise ValueError(
                    f"Found both 'definition' and 'description' in {mapping}. "
                    "Please use 'description'."
                )

        # k.replace("-", "_") is used convert e.g. "check-aggregate" to
        # "check_aggregated" since the former is a valid python variable name.
        return cls(
            name=name,
            **{
                k.replace("-", "_"): v
                for k, v in mapping.items()
                if k.replace("-", "_") in cls.named_attributes()
            },
            attributes={
                k: v
                for k, v in mapping.items()
                if k.replace("-", "_") not in cls.named_attributes()
            },
        )

    def set_attribute(self, key, value):
        self.attributes[key] = value

    @classmethod
    def named_attributes(cls) -> List[str]:
        return [a for a in cls.__dict__["__fields__"].keys() if a != "attributes"]

    @property
    def contains_tags(self) -> bool:
        return re.search("{.*}", self.name) is not None

    @property
    def tags(self):
        return re.findall("(?<={).*?(?=})", self.name)

    def replace_tag(self, tag: str, target):
        """Return a new instance with tag applied

        Parameters
        ----------
        tag : str
            Name of the tag
        target : _type_
            Code that is inserted

        Returns
        -------
        _type_
            new instance with occurrences of "{tag}" replaced by target
        """

        mapping = {
            key: value for key, value in self.dict().items() if key != "attributes"
        }
        mapping["name"] = mapping["name"].replace("{" + tag + "}", target.name)
        mapping["description"] = mapping["description"].replace(
            "{" + tag + "}", target.description
        )
        attributes = self.attributes.copy()
        for attr, value in target.attributes.items():
            if attr in attributes:
                attributes[attr] = attributes[attr].replace("{" + tag + "}", value)

        return self.__class__(**mapping, attributes=attributes)

    def __getattr__(self, k):
        try:
            return self.attributes[k]
        except KeyError as ke:
            raise AttributeError from ke

    def __setattr__(self, name, value):
        if name not in self.__class__.named_attributes():
            self.attributes[name] = value
        else:
            super().__setattr__(name, value)


class VariableCode(Code):

    unit: Optional[str]
    weight: Optional[str] = None
    region_aggregation: Optional[List[Dict[str, Dict]]] = None
    skip_region_aggregation: Optional[bool] = False
    method: Optional[str] = None
    check_aggregate: Optional[bool] = False
    components: Optional[Union[List[str], List[Dict[str, List[str]]]]] = None
