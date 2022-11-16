import re
from typing import Union, List, Dict, Optional, Set
from pydantic import BaseModel, StrictStr, StrictInt, StrictFloat, StrictBool, Field


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    description: Optional[str]
    extra_attributes: Union[
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
    ] = {}

    @classmethod
    def from_dict(cls, mapping) -> "Code":
        if isinstance(mapping, str):
            return cls(name=mapping)

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

        return cls(
            name=name,
            **{k: v for k, v in mapping.items() if k in cls.named_attributes()},
            extra_attributes={
                k: v for k, v in mapping.items() if k not in cls.named_attributes()
            },
        )

    def set_attribute(self, key, value):
        self.extra_attributes[key] = value

    @classmethod
    def named_attributes(cls) -> Set[str]:
        return {a for a in cls.__dict__["__fields__"].keys() if a != "extra_attributes"}

    @property
    def contains_tags(self) -> bool:
        return re.search("{.*}", self.name) is not None

    @property
    def tags(self):
        return re.findall("(?<={).*?(?=})", self.name)

    def replace_tag(self, tag: str, target: "Code") -> "Code":
        """Return a new instance with tag applied

        Parameters
        ----------
        tag : str
            Name of the tag
        target : Code
            Code attributes to be modified by the tag

        Returns
        -------
        Code
            New Code instance with occurrences of "{tag}" replaced by target
        """

        mapping = {
            key: value
            for key, value in self.dict().items()
            if key != "extra_attributes"
        }
        # replace name and description
        mapping["name"] = mapping["name"].replace("{" + tag + "}", target.name)
        mapping["description"] = mapping["description"].replace(
            "{" + tag + "}", target.description
        )

        # replace any other attribute
        extra_attributes = self.extra_attributes.copy()
        for attr, value in target.extra_attributes.items():
            if isinstance(extra_attributes.get(attr), str):
                extra_attributes[attr] = extra_attributes[attr].replace(
                    "{" + tag + "}", value
                )
            elif isinstance(mapping.get(attr), str):
                mapping[attr] = mapping[attr].replace("{" + tag + "}", value)
        return self.__class__(**mapping, extra_attributes=extra_attributes)

    def __getattr__(self, k):
        try:
            return self.extra_attributes[k]
        except KeyError as ke:
            raise AttributeError from ke

    def __setattr__(self, name, value):
        if name not in self.__class__.named_attributes():
            self.extra_attributes[name] = value
        else:
            super().__setattr__(name, value)


class VariableCode(Code):

    unit: Optional[Union[str, List[str]]] = Field(...)
    weight: Optional[str] = None
    region_aggregation: Optional[List[Dict[str, Dict]]] = Field(
        None, alias="region-aggregation"
    )
    skip_region_aggregation: Optional[bool] = Field(
        False, alias="skip-region-aggregation"
    )
    method: Optional[str] = None
    check_aggregate: Optional[bool] = Field(False, alias="check-aggregate")
    components: Optional[Union[List[str], List[Dict[str, List[str]]]]] = None

    class Config:
        # this allows using both "check_aggregate" and "check-aggregate" for attribute
        # setting
        allow_population_by_field_name = True

    @classmethod
    def named_attributes(cls) -> Set[str]:
        return (
            super()
            .named_attributes()
            .union(f.alias for f in cls.__dict__["__fields__"].values())
        )
