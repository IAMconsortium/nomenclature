import logging
from pathlib import Path
import textwrap
from typing import List, Union

import yaml
from pyam import IamDataFrame
from pyam.logging import adjust_log_level

from pydantic import model_validator

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import ErrorCollector
from nomenclature.processor.iamc import IamcDataFilter
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class DataValidationCriteria(IamcDataFilter):
    """Data validation criteria"""

    upper_bound: float = None
    lower_bound: float = None
    value: float = None
    rtol: float = None
    atol: float = None

    @model_validator(mode="before")
    @classmethod
    def check_validation_criteria_exist(cls, values):
        error = False
        # use value and rtol/atol
        if values.get("upper_bound") is None and values.get("lower_bound") is None:
            if values.get("value") is None:
                error = "No validation criteria provided."
        # use upper/lower bound
        else:
            if values.get("value") is not None:
                error = "Cannot use value and bounds simultaneously."
            if values.get("rtol") is not None or values.get("atol") is not None:
                error = "Cannot use tolerance with bounds. Use `value` instead."

        if error:
            raise ValueError(error + " Found " + str(values))

        return values


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: List[DataValidationCriteria]
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
                failed_validation = df.validate(**item.criteria)
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
