import abc
import logging
from pathlib import Path
from enum import IntEnum
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    computed_field,
)
from pyam import IamDataFrame
from toolkit.exceptions import NoTracebackException
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.processor import Processor

logger = logging.getLogger(__name__)


class WarningEnum(IntEnum):
    """Enum for warning levels."""

    error = 50
    high = 40
    medium = 30
    low = 20


class ValidationCriteria(abc.ABC, BaseModel):
    """Base class for validation criteria (value, bounds, range)."""

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
        """Validation criteria as read from the YAML file."""
        pass

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.criteria.items()])


class ValidationValue(ValidationCriteria):
    value: float | list
    rtol: float = 0.0
    atol: float = 0.0

    @property
    def tolerance(self) -> float | None:
        return (
            self.value * self.rtol + self.atol
            if isinstance(self.value, float)
            else None
        )

    @computed_field
    @property
    def upper_bound(self) -> float | None:
        return self.value + self.tolerance if isinstance(self.value, float) else None

    @computed_field
    @property
    def lower_bound(self) -> float | None:
        return self.value - self.tolerance if isinstance(self.value, float) else None

    @property
    def validation_args(self):
        # In case of list of values, validation is a hard equality check
        if isinstance(self.value, list):
            return {"value": self.value}
        # Else, return the bounds for tolerance check
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            include=["upper_bound", "lower_bound"],
        )

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            include=["value", "atol", "rtol"],
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
            exclude_none=True,
            exclude_unset=True,
            include=["upper_bound", "lower_bound"],
        )


class ValidationRange(ValidationCriteria):
    range: list[float] = Field(..., min_length=2, max_length=2)

    @field_validator("range", mode="after")
    @classmethod
    def check_range_is_valid(cls, value: list[float | int]) -> list[float | int]:
        if value[0] > value[1]:
            raise ValueError(
                "Validation 'range' must be given as `(lower_bound, upper_bound)`, "
                "found: " + str(value)
            )
        return value

    @computed_field
    @property
    def upper_bound(self) -> float:
        return self.range[1]

    @computed_field
    @property
    def lower_bound(self) -> float:
        return self.range[0]

    @property
    def validation_args(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            include=["upper_bound", "lower_bound"],
        )

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            include=["range"],
        )


class ValidationItem(BaseModel, abc.ABC):
    """Base class for validation items (criteria)."""

    name: str | None = None
    validation: list[ValidationValue | ValidationBounds | ValidationRange]

    @model_validator(mode="after")
    def check_warnings_order(self):
        """Check if warnings are set in descending order of severity."""
        if self.validation != sorted(
            self.validation, key=lambda c: c.warning_level, reverse=True
        ):
            raise ValueError(
                f"Validation criteria for {self.name} not sorted"
                " in descending order of severity."
            )
        else:
            return self

    @abc.abstractmethod
    def apply(self, df: IamDataFrame, fail_list: list, output_list: list):
        """Apply validation to IamDataFrame."""
        pass


class Validator(Processor):
    """Abstract validation and processing class."""

    criteria_items: list[ValidationItem]
    file: Path | str
    output_path: Path | None = None
    exception_cls: type[NoTracebackException] = NoTracebackException

    @classmethod
    @abc.abstractmethod
    def from_file(
        cls, file: Path | str, output_path: Path | str | None = None
    ) -> "Validator":
        """Create a Validator instance from a file."""
        pass

    @abc.abstractmethod
    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        """Validate the criteria items against a :class:`DataStructureDefinition`.

        Checks that all codes referenced in the criteria exist in the provided definition.

        Parameters
        ----------
        dsd : DataStructureDefinition
            Data structure definition to validate against.

        Raises
        ------
        ExceptionGroup
            If any criteria item references unknown codes.
        """
        pass

    @abc.abstractmethod
    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Apply validation to IamDataFrame.

        Logs warning/error messages for each criterion that is not met.

        Parameters
        ----------
        df : pyam.IamDataFrame
            Data in IAMC format to be validated

        Returns
        -------
        pyam.IamDataFrame

        Raises
        ------
        ValueError
        """
        pass
