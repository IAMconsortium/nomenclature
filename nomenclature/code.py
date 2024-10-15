import json
import re
from keyword import iskeyword
from pathlib import Path
from typing import Any, Dict, List, Set, Union, Optional
from pydantic import (
    field_validator,
    field_serializer,
    ConfigDict,
    BaseModel,
    Field,
    ValidationInfo,
)

from nomenclature.error import ErrorCollector

from pyam.utils import to_list

from .countries import countries


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    description: str | None = None
    file: Union[str, Path] | None = None
    extra_attributes: Dict[str, Any] = {}
    repository: str | None = None

    def __eq__(self, other) -> bool:
        return self.model_dump(exclude="file") == other.model_dump(exclude="file")

    @field_validator("extra_attributes")
    @classmethod
    def check_attribute_names(
        cls, v: Dict[str, Any], info: ValidationInfo
    ) -> Dict[str, Any]:
        # Check that attributes only contains keys which are valid identifiers
        if illegal_keys := [
            key for key in v.keys() if not key.isidentifier() or iskeyword(key)
        ]:
            raise ValueError(
                "Only valid identifiers are allowed as attribute keys. Found "
                f"'{illegal_keys}' in '{info.data['name']}' which are not allowed."
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
        return {a for a in cls.model_fields if a != "extra_attributes"}

    @property
    def contains_tags(self) -> bool:
        return re.search("{.*}", self.name) is not None

    @property
    def tags(self):
        return re.findall("(?<={).*?(?=})", self.name)

    @property
    def flattened_dict(self):
        return {
            **self.model_dump(
                by_alias=True, exclude_unset=True, exclude="extra_attributes"
            ),
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

        def _replace_or_recurse(_attr, _value):
            # if the attribute is a string and contains "{tag}" replace
            if isinstance(_value, str) and "{" + tag + "}" in _value:
                # if the the target has the corresponding attribute replace
                if _attr in target.flattened_dict:
                    return _value.replace("{" + tag + "}", getattr(target, _attr))
                # otherwise return the name
                else:
                    return _value.replace("{" + tag + "}", getattr(target, "name"))
            # if the attribute is a list, iterate over the items and replace tags
            elif isinstance(_value, list):
                return [_replace_or_recurse(_attr, _v) for _v in _value]
            # if the attribute is a mapping, iterate over the items and replace tags
            # in the values (not the keys)
            elif isinstance(_value, dict):
                return {_k: _replace_or_recurse(attr, _v) for _k, _v in _value.items()}
            # otherwise return as is
            else:
                return _value

        mapping = {}
        for attr, value in self.flattened_dict.items():
            mapping[attr] = _replace_or_recurse(attr, value)
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
    unit: Union[str, List[str]] = Field(...)
    weight: str | None = None
    region_aggregation: List[Dict[str, Dict]] | None = Field(
        default=None, alias="region-aggregation"
    )
    skip_region_aggregation: bool | None = Field(
        default=False, alias="skip-region-aggregation"
    )
    method: str | None = None
    check_aggregate: bool | None = Field(default=False, alias="check-aggregate")
    components: Union[List[str], List[Dict[str, List[str]]]] | None = None
    drop_negative_weights: bool | None = None
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("region_aggregation", "components", "unit", mode="before")
    @classmethod
    def deserialize_json(cls, v):
        try:
            return json.loads(v) if isinstance(v, str) else v
        except json.decoder.JSONDecodeError:
            return v

    @field_validator("unit", mode="before")
    def convert_none_to_empty_string(cls, v):
        return v if v is not None else ""

    @field_serializer("unit")
    def convert_str_to_none_for_writing(self, v):
        return v if v != "" else None

    @property
    def units(self) -> List[str]:
        return self.unit if isinstance(self.unit, list) else [self.unit]

    @classmethod
    def named_attributes(cls) -> Set[str]:
        return (
            super().named_attributes().union(f.alias for f in cls.model_fields.values())
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
    countries : list of str, optional
        List of countries in that region
    iso3_codes : str or list of str, optional
        ISO3 codes of countries in that region

    """

    hierarchy: str = None
    countries: Optional[List[str]] = None
    iso3_codes: Optional[Union[List[str], str]] = None

    @field_validator("countries", mode="before")
    def check_countries(cls, v: List[str], info: ValidationInfo) -> List[str]:
        """Verifies that each country name is defined in `nomenclature.countries`."""
        v = to_list(v)
        if invalid_country_names := set(v) - set(countries.names):
            raise ValueError(
                f"Region '{info.data['name']}' uses non-standard country name(s): "
                + ", ".join(invalid_country_names)
                + "\nPlease use `nomenclature.countries` for consistency. (https://"
                + "nomenclature-iamc.readthedocs.io/en/stable/api/countries.html)"
            )
        return v

    @field_validator("iso3_codes")
    def check_iso3_codes(cls, v: List[str], info: ValidationInfo) -> List[str]:
        """Verifies that each ISO3 code is valid according to pycountry library."""
        errors = ErrorCollector()
        if invalid_iso3_codes := [
            iso3_code
            for iso3_code in to_list(v)
            if countries.get(alpha_3=iso3_code) is None
        ]:
            errors.append(
                ValueError(
                    f"Region '{info.data['name']}' has invalid ISO3 country code(s): "
                    + ", ".join(invalid_iso3_codes)
                )
            )
        if errors:
            raise ValueError(errors)
        return v


class MetaCode(Code):
    """Code object with allowed values list

    Attributes
    ----------
    allowed_values : Optional(list[any])
        An optional list of allowed values

    """

    allowed_values: List[Any] | None = None
