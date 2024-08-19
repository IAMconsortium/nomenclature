import logging
from pathlib import Path
from typing import List, Union

import yaml
from pyam import IamDataFrame
from pyam.logging import adjust_log_level

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
        failed_validation_list = []
        error = False

        with adjust_log_level():
            for item in self.criteria_items:
                failed_validation = df.validate(**item.criteria)
                if failed_validation is not None:
                    for direction in ["upper_bound", "lower_bound"]:
                        if getattr(item, direction) is not None:
                            failed_validation[direction] = getattr(item, direction)
                    failed_validation_list.append(
                        f"Criteria: {item.criteria}\n{failed_validation}\n"
                    )

            if failed_validation_list:
                logger.error(
                    "Failed data validation (file %s):\n%s",
                    get_relative_path(self.file),
                    "\n".join(failed_validation_list),
                )
                error = True

            if error:
                raise ValueError(
                    "Data validation failed. Please check the log for details."
                )
        return df

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors = ErrorCollector(description=f"in file '{self.file}'")
        for item in self.criteria_items:
            try:
                item.validate_with_definition(dsd)
            except ValueError as value_error:
                errors.append(value_error)
        if errors:
            raise ValueError(errors)
