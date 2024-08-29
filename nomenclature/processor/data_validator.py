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
    rtol: Optional[float] = None
    atol: Optional[float] = None

    def get_validation_args(self):
        _criteria = self.criteria.copy()
        value = _criteria.pop("value")
        tolerance = value * _criteria.pop("rtol", 0) + _criteria.pop("atol", 0)
        _criteria["upper_bound"] = value + tolerance
        _criteria["lower_bound"] = value - tolerance
        return _criteria


class DataValidationCriteriaBounds(IamcDataFilter):
    upper_bound: Optional[float] = None
    lower_bound: Optional[float] = None

    @model_validator(mode="before")
    def check_validation_criteria_exist(cls, values):
        if values.get("upper_bound") is None and values.get("lower_bound") is None:
            raise ValueError(
                "No validation criteria provided. Found " + str(cls.criteria)
            )
        return values

    def get_validation_args(self):
        return self.criteria


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: List[DataValidationCriteriaBounds | DataValidationCriteriaValue]
    file: Path

    @classmethod
    def from_file(cls, file: Union[Path, str]) -> "DataValidator":
        with open(file, "r") as f:
            content = yaml.safe_load(f)
        return cls(file=file, criteria_items=content)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        error_list = []

        with adjust_log_level():
            for item in self.criteria_items:
                failed_validation = df.validate(**item.get_validation_args())
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
