import logging
import textwrap
from enum import Enum
from pathlib import Path

import yaml
from pyam import IamDataFrame
from pyam.logging import adjust_log_level
from pydantic import computed_field, field_validator, model_validator

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import ErrorCollector
from nomenclature.processor import Processor
from nomenclature.processor.iamc import IamcDataFilter
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class WarningEnum(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    error = "error"


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
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level", "value", "rtol", "atol"],
        )

    @property
    def criteria(self):
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
            exclude_none=True,
            exclude_unset=True,
            exclude=["warning_level"],
        )


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: list[DataValidationCriteriaBounds | DataValidationCriteriaValue]
    file: Path

    @field_validator("criteria_items", mode="before")
    def check_criteria(cls, v):
        for criterion in v:
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
        return cls(file=file, criteria_items=content)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        fail_list = []
        error = False

        with adjust_log_level():
            for item in self.criteria_items:
                failed_validation = df.validate(**item.validation_args)
                if failed_validation is not None:
                    criteria_msg = "  Criteria: " + ", ".join(
                        [f"{key}: {value}" for key, value in item.criteria.items()]
                    )
                    failed_validation["warning_level"] = item.warning_level.value
                    if item.warning_level == WarningEnum.error:
                        error = True
                    fail_list.append(criteria_msg)
                    fail_list.append(
                        textwrap.indent(str(failed_validation), prefix="    ") + "\n"
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
