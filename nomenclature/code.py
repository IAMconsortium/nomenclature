import json
import re
from keyword import iskeyword
from pathlib import Path
from typing import Any

from pyam.utils import to_list
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_serializer,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from nomenclature.error import ErrorCollector

from .countries import countries


class Code(BaseModel):
    """A simple class for a mapping of a "code" to its attributes"""

    name: str
    description: str | None = None
    file: str | Path | None = None
    extra_attributes: dict[str, Any] = {}
    repository: str | None = None

    def __eq__(self, other) -> bool:
        return self.model_dump(exclude="file") == other.model_dump(exclude="file")

    @field_validator("extra_attributes")
    @classmethod
    def check_attribute_names(
        cls, v: dict[str, Any], info: ValidationInfo
    ) -> dict[str, Any]:
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
    def named_attributes(cls) -> set[str]:
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

    @property
    def depth(self) -> int:
        return self.name.count("|")

    @property
    def from_external_repository(self) -> bool:
        return self.repository is not None

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
                # if the target has the attribute, replace the tag with the value
                if _attr in target.flattened_dict:
                    return _value.replace("{" + tag + "}", getattr(target, _attr))
                # otherwise return the name
                else:
                    return _value.replace("{" + tag + "}", getattr(target, "name"))
            # if the attribute is an integer and "tier"
            elif _attr == "tier" and isinstance(_value, int):
                # if tier in tag is str formatted as "^1"/"^2"
                if (tag_tier := getattr(target, _attr, None)) in {"^1", "^2"}:
                    return _value + int(tag_tier[-1])
                # if tag doesn't have tier attribute
                elif not tag_tier:
                    return _value
                # else misformatted tier in tag
                else:
                    raise ValueError(
                        f"Invalid 'tier' attribute in '{tag}' tag '{target.name}': {tag_tier}\n"
                        "Allowed values are '^1' or '^2'."
                    )
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
    unit: str | list[str] = Field(...)
    tier: int | str | None = None
    weight: str | None = None
    region_aggregation: list[dict[str, dict]] | None = Field(
        default=None, alias="region-aggregation"
    )
    skip_region_aggregation: bool | None = Field(
        default=False, alias="skip-region-aggregation"
    )
    method: str | None = None
    check_aggregate: bool | None = Field(default=False, alias="check-aggregate")
    components: list[str] | dict[str, list[str]] | None = None
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
    @classmethod
    def convert_none_to_empty_string(cls, v):
        return v if v is not None else ""

    @model_validator(mode="after")
    def wildcard_must_skip_region_aggregation(self) -> Self:
        if self.is_wildcard and self.skip_region_aggregation is False:
            raise ValueError(
                f"Wildcard variable '{self.name}' must skip region aggregation"
            )
        return self

    @field_validator("components", mode="before")
    @classmethod
    def cast_variable_components_args(cls, v):
        """Cast "components" list of dicts to a codelist"""

        # translate a list of single-key dictionaries to a simple dictionary
        if v is not None and isinstance(v, list) and isinstance(v[0], dict):
            comp = {}
            for val in v:
                comp.update(val)
            return comp
        return v

    @field_serializer("unit")
    def convert_str_to_none_for_writing(self, v):
        return v if v != "" else None

    @property
    def is_wildcard(self) -> bool:
        return "*" in self.name

    @property
    def units(self) -> list[str]:
        return self.unit if isinstance(self.unit, list) else [self.unit]

    @classmethod
    def named_attributes(cls) -> set[str]:
        return (
            super().named_attributes().union(f.alias for f in cls.model_fields.values())
        )

    @property
    def pyam_agg_kwargs(self) -> dict[str, Any]:
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
    def agg_kwargs(self) -> dict[str, Any]:
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
    countries: list[str] | None = None
    iso3_codes: list[str] | str | None = None

    @field_validator("countries", mode="before")
    @classmethod
    def check_countries(cls, v: list[str], info: ValidationInfo) -> list[str]:
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
    @classmethod
    def check_iso3_codes(cls, v: list[str], info: ValidationInfo) -> list[str]:
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

    @property
    def is_directional(self) -> bool:
        return ">" in self.name

    @property
    def destination(self) -> str:
        if not self.is_directional:
            raise ValueError("Non directional region does not have a destination")
        return self.name.split(">")[1]

    @property
    def origin(self) -> str:
        if not self.is_directional:
            raise ValueError("Non directional region does not have an origin")
        return self.name.split(">")[0]


class MetaCode(Code):
    """Code object with allowed values list

    Attributes
    ----------
    allowed_values : list[Any], optional
        An optional list of allowed values

    """

    allowed_values: list[Any] | None = None
