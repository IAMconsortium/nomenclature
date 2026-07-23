import abc
import logging
import pandas as pd
from pathlib import Path
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
from pyam.utils import adjust_log_level
from toolkit.exceptions import NoTracebackException
from nomenclature.codelist import CodeList
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.processor import Processor
from nomenclature.utils import get_relative_path

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
    def filter_args(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["validation", "name"]
        )

    @abc.abstractmethod
    def apply(self, df: IamDataFrame, fail_list: list, output_list: list):
        """Apply validation to IamDataFrame."""
        pass

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.filter_args.items()])


class Validator(Processor):
    """Abstract validation and processing class"""

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

    @classmethod
    @abc.abstractmethod
    def from_codelist(
        cls, codelist: CodeList, output_path: Path | None = None
    ) -> "Validator":
        """Create a Validator from a CodeList"""
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

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Validates data in IAMC format according to specified criteria.

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
            :exc:`ValueError` if any criterion has a warning level of ``error``
        """

        error_list: list[bool] = []
        fail_list: list[str] = []
        output_list: list[pd.DataFrame] = []

        with adjust_log_level():
            for item in self.criteria_items:
                error, fail_list, output_list = item.apply(df, fail_list, output_list)
                error_list.append(error)
            if self.output_path:
                pd.concat(output_list).to_excel(self.output_path, index=False)
            fail_msg = f"(file {get_relative_path(self.file)}):\n"
            if any(error_list):
                raise self.exception_cls(fail_list, self.file)
            if fail_list:
                fail_msg = (
                    "Data validation with warning(s) " + fail_msg + "\n".join(fail_list)
                )
                logger.warning(fail_msg)
        return df
