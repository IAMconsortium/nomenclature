import json
import re
import pyam
import pycountry
from keyword import iskeyword
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field, validator


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    description: Optional[str]
    file: Optional[Union[str, Path]] = None
    extra_attributes: Dict[str, Any] = {}

    def __eq__(self, other) -> bool:
        return {key: value for key, value in self.dict().items() if key != "file"} == {
            key: value for key, value in other.dict().items() if key != "file"
        }

    @validator("extra_attributes")
    def check_attribute_names(cls, v, values):
        # Check that attributes only contains keys which are valid identifiers
        if illegal_keys := [
            key for key in v.keys() if not key.isidentifier() or iskeyword(key)
        ]:
            raise ValueError(
                "Only valid identifiers are allowed as attribute keys. Found "
                f"'{illegal_keys}' in '{values['name']}' which are not allowed."
            )
        return v

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

    @classmethod
    def named_attributes(cls) -> Set[str]:
        return {a for a in cls.__dict__["__fields__"].keys() if a != "extra_attributes"}

    @property
    def contains_tags(self) -> bool:
        return re.search("{.*}", self.name) is not None

    @property
    def tags(self):
        return re.findall("(?<={).*?(?=})", self.name)

    @property
    def flattened_dict(self):
        fields_set_alias = {
            self.__fields__[field].alias for field in self.__fields_set__
        }
        return {
            **{
                k: v
                for k, v in self.dict(by_alias=True).items()
                if k != "extra_attributes" and k in fields_set_alias
            },
            **self.extra_attributes,
        }

    @property
    def flattened_dict_serialized(self):
        return {
            key: (json.dumps(value) if isinstance(value, (list, dict)) else value)
            for key, value in self.flattened_dict.items()
        }

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

        mapping = {}
        for attr, value in self.flattened_dict.items():
            # if the attribute is a string and contains "{tag}" replace
            if isinstance(value, str) and "{" + tag + "}" in value:
                # if the the target has the corresponding attribute replace
                if attr in target.flattened_dict:
                    mapping[attr] = value.replace(
                        "{" + tag + "}", getattr(target, attr)
                    )
                # otherwise insert the name
                else:
                    mapping[attr] = value.replace("{" + tag + "}", target.name)
            # otherwise append as is
            else:
                mapping[attr] = value
        name = mapping["name"]
        del mapping["name"]
        return self.__class__.from_dict({name: mapping})

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
    drop_negative_weights: Optional[bool] = None

    class Config:
        # this allows using both "check_aggregate" and "check-aggregate" for attribute
        # setting
        allow_population_by_field_name = True

    @validator("region_aggregation", "components", "unit", pre=True)
    def deserialize_json(cls, v):
        try:
            return json.loads(v) if isinstance(v, str) else v
        except json.decoder.JSONDecodeError:
            return v

    @property
    def units(self) -> List[Union[str, None]]:
        return self.unit if isinstance(self.unit, list) else [self.unit]

    @classmethod
    def named_attributes(cls) -> Set[str]:
        return (
            super()
            .named_attributes()
            .union(f.alias for f in cls.__dict__["__fields__"].values())
        )

    @property
    def pyam_agg_kwargs(self) -> Dict[str, Any]:
        # return a dict of all not None pyam aggregation properties
        return {
            field: getattr(self, field)
            for field in (
                "weight",
                "method",
                "components",
                "drop_negative_weights",
            )
            if getattr(self, field) is not None
        }

    @property
    def agg_kwargs(self) -> Dict[str, Any]:
        return (
            {**self.pyam_agg_kwargs, **{"region_aggregation": self.region_aggregation}}
            if self.region_aggregation is not None
            else self.pyam_agg_kwargs
        )


class RegionCode(Code):
    """A subclass of Code specified for regions

    Attributes
    ----------
    name : str
        Name of the RegionCode
    hierarchy : str
        Hierarchy of the RegionCode
    iso3_codes : str or list of str
        ISO3 codes of countries in that region

    """

    hierarchy: str = None
    iso3_codes: Union[List[str], str] = None

    @validator("iso3_codes")
    def check_iso3_codes(cls, v, values) -> List[str]:
        """Verifies that each ISO3 code is valid according to pycountry library."""
        if invalid_iso3_codes := [
            iso3_code
            for iso3_code in pyam.to_list(v)
            if pycountry.countries.get(alpha_3=iso3_code) is None
        ]:
            raise ValueError(
                f"Region '{values['name']}' has invalid ISO3 country code(s): "
                + ", ".join(invalid_iso3_codes)
            )
        return v


class MetaCode(Code):
    """Code object with allowed values list

    Attributes
    ----------
    allowed_values : Optional(list[any])
        An optional list of allowed values

    """

    allowed_values: Optional[List[Any]]
