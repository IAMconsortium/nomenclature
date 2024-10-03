import logging
import textwrap
from pathlib import Path
from typing import List, Optional, Union

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


class DataValidationCriteriaValue(IamcDataFilter):
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
            exclude=["value", "rtol", "atol"],
        )

    @property
    def criteria(self):
        return self.model_dump(
            exclude_none=True,
            exclude_unset=True,
            exclude=["lower_bound", "upper_bound"],
        )


class DataValidationCriteriaBounds(IamcDataFilter):
    upper_bound: Optional[float] = None
    lower_bound: Optional[float] = None

    @model_validator(mode="after")
    def check_validation_criteria_exist(self):
        if self.upper_bound is None and self.lower_bound is None:
            raise ValueError("No validation criteria provided: " + str(self.criteria))
        return self

    @property
    def validation_args(self):
        return self.criteria


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: List[DataValidationCriteriaBounds | DataValidationCriteriaValue]
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
    def from_file(cls, file: Union[Path, str]) -> "DataValidator":
        with open(file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        return cls(file=file, criteria_items=content)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        error_list = []

        with adjust_log_level():
            for item in self.criteria_items:
                failed_validation = df.validate(**item.validation_args)
                if failed_validation is not None:
                    error_list.append(
                        "  Criteria: "
                        + ", ".join(
                            [f"{key}: {value}" for key, value in item.criteria.items()]
                        )
                    )
                    error_list.append(
                        textwrap.indent(str(failed_validation), prefix="    ") + "\n"
                    )

            if error_list:
                logger.error(
                    "Failed data validation (file %s):\n%s",
                    get_relative_path(self.file),
                    "\n".join(error_list),
                )
                raise ValueError(
                    "Data validation failed. Please check the log for details."
                )
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
