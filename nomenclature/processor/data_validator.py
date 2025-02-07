import logging
import textwrap
from enum import Enum
from pathlib import Path

import yaml
from pandas import concat
from pyam import IamDataFrame
from pyam.logging import adjust_log_level
from pydantic import computed_field, field_validator, model_validator, Field

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import ErrorCollector
from nomenclature.processor import Processor
from nomenclature.processor.iamc import IamcDataFilter
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class WarningEnum(str, Enum):
    error = "error"
    high = "high"
    medium = "medium"
    low = "low"


class DataValidationCriteria(IamcDataFilter):
    warning_level: WarningEnum = WarningEnum.error


class DataValidationCriteriaValue(DataValidationCriteria):
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


class DataValidationCriteriaBounds(DataValidationCriteria):
    upper_bound: float | None = None
    lower_bound: float | None = None

    @model_validator(mode="after")
    def check_validation_criteria_exist(self):
        if self.upper_bound is None and self.lower_bound is None:
            raise ValueError("No validation criteria provided: " + str(self.criteria))
        return self

    @property
    def validation_args(self):
        return self.criteria

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["warning_level"]
        )


class DataValidationCriteriaRange(DataValidationCriteria):
    range: list[float] = Field(..., min_length=2, max_length=2)

    @model_validator(mode="after")
    def check_range_is_valid(self):
        if self.range[0] > self.range[1]:
            raise ValueError("Validation range is invalid: " + str(self.criteria))
        return self

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


class DataValidationCriteriaMultiple(IamcDataFilter):
    validation: (
        list[
            DataValidationCriteriaValue
            | DataValidationCriteriaBounds
            | DataValidationCriteriaRange
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def check_warnings_order(self):
        """Check if warnings are set in descending order of severity."""
        if self.validation != sorted(self.validation, key=lambda c: c.warning_level):
            raise ValueError(
                f"Validation criteria for {self.criteria} not"
                " in descending order of severity."
            )
        else:
            return self

    @property
    def criteria(self):
        """Attributes used for validation (as specified in the file)."""
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["validation"]
        )


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: list[DataValidationCriteriaMultiple]
    file: Path

    @field_validator("criteria_items", mode="before")
    def check_criteria(cls, v):
        for item in v:
            for criterion in item["validation"]:
                has_bounds = any(c in criterion for c in ["upper_bound", "lower_bound"])
                has_values = any(c in criterion for c in ["value", "atol", "rtol"])
            if has_bounds and has_values:
                raise ValueError(
                    f"Cannot use bounds and value-criteria simultaneously: {criterion}"
                )
        return v

    @classmethod
    def from_file(cls, file: Path | str) -> "DataValidator":
        with open(file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        criteria_items = []
        for item in content:
            filter_args = {k: item[k] for k in item if k in IamcDataFilter.model_fields}
            criteria_args = {
                k: item[k]
                for k in item
                if k not in IamcDataFilter.model_fields and k != "validation"
            }
            if "validation" in item:
                for criterion in item["validation"]:
                    criterion.update(filter_args)
            else:
                item["validation"] = [{**filter_args, **criteria_args}]
            criteria_items.append({k: item[k] for k in item if k not in criteria_args})
        return cls(file=file, criteria_items=criteria_items)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        fail_list = []
        error = False

        with adjust_log_level():
            for item in self.criteria_items:
                per_item_df = df
                for criterion in item.validation:
                    failed_validation = per_item_df.validate(
                        **criterion.validation_args
                    )
                    if failed_validation is not None:
                        per_item_df = IamDataFrame(
                            concat([df.data, failed_validation]).drop_duplicates(
                                keep=False
                            )
                        )
                        criteria_msg = "  Criteria: " + ", ".join(
                            [
                                f"{key}: {value}"
                                for key, value in criterion.criteria.items()
                            ]
                        )
                        failed_validation["warning_level"] = (
                            criterion.warning_level.value
                        )
                        if criterion.warning_level == WarningEnum.error:
                            error = True
                        fail_list.append(criteria_msg)
                        fail_list.append(
                            textwrap.indent(str(failed_validation), prefix="    ")
                            + "\n"
                        )
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
