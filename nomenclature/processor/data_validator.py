import logging
import textwrap
from enum import IntEnum
from pathlib import Path

import yaml
import pandas as pd
from pyam import IamDataFrame
from pyam.logging import adjust_log_level
from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
    Field,
)

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import ErrorCollector
from nomenclature.processor import Processor
from nomenclature.processor.iamc import IamcDataFilter
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class WarningEnum(IntEnum):
    error = 50
    high = 40
    medium = 30
    low = 20


class DataValidationCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warning_level: WarningEnum = WarningEnum.error

    @field_validator("warning_level", mode="before")
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
    def criteria(self):
        pass

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.criteria.items()])


class DataValidationValue(DataValidationCriteria):
    value: float
    rtol: float = 0.0
    atol: float = 0.0

    @property
    def tolerance(self) -> float:
        return self.value * self.rtol + self.atol

    @computed_field
    def upper_bound(self) -> float:
        return self.value + self.tolerance

    @computed_field
    def lower_bound(self) -> float:
        return self.value - self.tolerance

    @property
    def validation_args(self):
        """Attributes used for validation (as bounds)."""
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level", "value", "rtol", "atol"],
        )

    @property
    def criteria(self):
        """Attributes used for validation (as specified in the file)."""
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level", "lower_bound", "upper_bound"],
        )


class DataValidationBounds(DataValidationCriteria):
    # allow extra but raise error to guard against multiple criteria
    model_config = ConfigDict(extra="allow")

    upper_bound: float | None = None
    lower_bound: float | None = None

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


class DataValidationRange(DataValidationCriteria):
    range: list[float] = Field(..., min_length=2, max_length=2)

    @field_validator("range", mode="after")
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
        """Attributes used for validation (as bounds)."""
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


class DataValidationItem(IamcDataFilter):
    validation: list[DataValidationValue | DataValidationRange | DataValidationBounds]

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
        """Attributes used for validation (as specified in the file)."""
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["validation"]
        )

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.filter_args.items()])

    def apply(self, df: IamDataFrame, fail_list: list) -> IamDataFrame:
        error = False
        per_item_df = df.filter(**self.filter_args)
        for criterion in self.validation:
            failed_validation = per_item_df.validate(**criterion.validation_args)
            if failed_validation is not None:
                per_item_df = IamDataFrame(
                    pd.concat([per_item_df.data, failed_validation]).drop_duplicates(
                        keep=False
                    )
                )
                failed_validation["warning_level"] = criterion.warning_level.name
                failed_validation["criteria"] = str(criterion)
                if criterion.warning_level == WarningEnum.error:
                    error = True
                fail_list.append("  Criteria: " + str(self) + ", " + str(criterion))
                fail_list.append(
                    textwrap.indent(
                        failed_validation.iloc[:, :-1].to_string(), prefix="  "
                    )
                    + "\n"
                )
        return error


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: list[DataValidationItem]
    file: Path

    @classmethod
    def from_file(cls, file: Path | str) -> "DataValidator":
        with open(file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        criteria_items = []
        for item in content:
            # handling of simple case where filter and criteria args are given at the same level
            if "validation" not in item:
                filter_args = {
                    k: item[k] for k in item if k in IamcDataFilter.model_fields
                }
                criteria_args = [
                    {
                        k: item[k]
                        for k in item
                        if k not in IamcDataFilter.model_fields and k != "validation"
                    }
                ]
                item = dict(**filter_args, validation=criteria_args)
            criteria_items.append(item)
        return cls(file=file, criteria_items=criteria_items)  # type: ignore

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Validates data in IAMC format according to specified criteria.

        Logs warning/error messages for each criterion that is not met.

        Parameters
        ----------
        df : IamDataFrame
            Data in IAMC format to be validated

        Returns
        -------
        IamDataFrame

        Raises
        ------
            `ValueError` if any criterion has a warning level of `error`
        """

        fail_list = []

        with adjust_log_level():
            error = any([item.apply(df, fail_list) for item in self.criteria_items])
            fail_msg = "(file %s):\n" % get_relative_path(self.file)
            if error:
                fail_msg = (
                    "Data validation with error(s)/warning(s) "
                    + fail_msg
                    + "\n".join(fail_list)
                )
                logger.error(fail_msg)
                raise ValueError(
                    "Data validation failed. Please check the log for details."
                )
            if fail_list:
                fail_msg = (
                    "Data validation with warning(s) " + fail_msg + "\n".join(fail_list)
                )
                logger.warning(fail_msg)
        return df

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors = ErrorCollector(description=f"in file '{self.file}'")
        for criterion in self.criteria_items:
            try:
                criterion.validate_with_definition(dsd)
            except ValueError as value_error:
                errors.append(value_error)
        if errors:
            raise ValueError(errors)
