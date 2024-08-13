from pathlib import Path
from typing import List, Union

import yaml

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import ErrorCollector
from nomenclature.processor.iamc import IamcDataFilter
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path


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

    def apply(self):
        pass

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors = ErrorCollector(description=f"in file '{self.file}'")
        for data in self.criteria_items:
            try:
                data.validate_with_definition(dsd)
            except ValueError as value_error:
                errors.append(value_error)
        if errors:
            raise ValueError(errors)
