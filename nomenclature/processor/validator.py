import abc
import logging

from enum import IntEnum
from typing import Any
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    computed_field,
)
from pyam import IamDataFrame

logger = logging.getLogger(__name__)


class WarningEnum(IntEnum):
    error = 50
    high = 40
    medium = 30
    low = 20


class ValidationCriteria(abc.ABC, BaseModel):
    """Base class for validation criteria (value, bounds, range)"""

    warning_level: WarningEnum = WarningEnum.error

    model_config = ConfigDict(extra="forbid")

    @field_validator("warning_level", mode="before")
    @classmethod
    def validate_warning_level(cls, value):
        if isinstance(value, str):
            try:
                return WarningEnum[value]
            except KeyError:
                raise ValueError(
                    f"Invalid warning level: {value}. Expected one of:"
                    f" {', '.join(level.name for level in WarningEnum)}"
                )
        return value

    @property
    @abc.abstractmethod
    def validation_args(self):
        """Attributes used for validation."""
        pass

    @property
    @abc.abstractmethod
    def criteria(self):
        """Attributes used for validation (as specified in the file)."""
        pass

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.criteria.items()])


class ValidationValue(ValidationCriteria):
    value: Any

    @property
    def validation_args(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level"],
        )

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level"],
        )


class ValidationBounds(ValidationCriteria):
    upper_bound: float | None = None
    lower_bound: float | None = None

    # Allow extra but raise error to guard against multiple criteria
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_validation_criteria_exist(self):
        if self.upper_bound is None and self.lower_bound is None:
            raise ValueError("No validation criteria provided: " + str(self.criteria))
        return self

    @model_validator(mode="after")
    def check_validation_multiple_criteria(self):
        if self.model_extra:
            raise ValueError(
                "Must use either bounds, range or value, found: " + str(self.criteria)
            )
        return self

    @property
    def validation_args(self):
        return self.criteria

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["warning_level"]
        )


class ValidationRange(ValidationCriteria):
    range: list[float] = Field(..., min_length=2, max_length=2)

    @field_validator("range", mode="after")
    @classmethod
    def check_range_is_valid(cls, value: list[float]):
        if value[0] > value[1]:
            raise ValueError(
                "Validation 'range' must be given as `(lower_bound, upper_bound)`, "
                "found: " + str(value)
            )
        return value

    @computed_field
    def upper_bound(self) -> float:
        return self.range[1]

    @computed_field
    def lower_bound(self) -> float:
        return self.range[0]

    @property
    def validation_args(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level", "range"],
        )

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level", "lower_bound", "upper_bound"],
        )


class ValidationItem(BaseModel, abc.ABC):
    """Base class for validation items (filter + criteria)"""

    name: str | None = None
    validation: list[ValidationValue | ValidationBounds | ValidationRange]

    @model_validator(mode="after")
    def check_warnings_order(self):
        """Check if warnings are set in descending order of severity."""
        if self.validation != sorted(
            self.validation, key=lambda c: c.warning_level, reverse=True
        ):
            raise ValueError(
                f"Validation criteria for {self.criteria} not sorted"
                " in descending order of severity."
            )
        else:
            return self

    @property
    @abc.abstractmethod
    def filter_args(self):
        """Dimensions and values used to filter rows to be validated."""
        pass

    @abc.abstractmethod
    def apply(self, df: IamDataFrame, fail_list: list, output_list: list):
        """Apply validation to IamDataFrame."""
        pass

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.filter_args.items()])
