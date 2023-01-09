import logging
from pathlib import Path
from typing import List, Optional, Union, Tuple

import yaml
from pyam import IamDataFrame
import pydantic
from pydantic import BaseModel, validator
from pydantic.error_wrappers import ErrorWrapper

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.utils import get_relative_path
from nomenclature.error.required_data import RequiredDataMissingError

logger = logging.getLogger(__name__)


class RequiredData(BaseModel):

    variable: List[str]
    region: Optional[List[str]]
    year: Optional[List[int]]
    unit: Optional[str]

    @validator("variable", "region", "year", pre=True)
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        error_msg = ""

        # check for undefined regions and variables
        for dim in ("region", "variable"):
            values = self.__getattribute__(dim) or []
            invalid = dsd.__getattribute__(dim).validate_items(values)
            if invalid:
                error_msg += (
                    f"The following {dim}(s) were not found in the "
                    f"DataStructureDefinition:\n{invalid}\n"
                )
        # check for defined variables with wrong units
        if wrong_unit_variables := self._wrong_unit_variables(dsd):
            error_msg += (
                "The following variables were found in the "
                "DataStructureDefinition but have the wrong unit "
                "(affected variable, wrong unit, expected unit):\n"
                f"{wrong_unit_variables}"
            )

        if error_msg:
            raise ValueError(error_msg)

    def _wrong_unit_variables(
        self, dsd: DataStructureDefinition
    ) -> List[Tuple[str, str, str]]:
        wrong_units: List[Tuple[str, str, str]] = []
        if hasattr(dsd, "variable"):
            wrong_units.extend(
                (var, self.unit, getattr(dsd, "variable")[var].unit)
                for var in getattr(self, "variable")
                if var in getattr(dsd, "variable")  # check if the variable exists
                and self.unit  # check if a unit is specified
                and self.unit not in getattr(dsd, "variable")[var].units
            )

        return wrong_units


class RequiredDataValidator(BaseModel):

    name: str
    required_data: List[RequiredData]
    file: Path

    @classmethod
    def from_file(cls, file: Union[Path, str]) -> "RequiredDataValidator":
        with open(file, "r") as f:
            content = yaml.safe_load(f)
        return cls(file=file, **content)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        error = False
        # check for required data and raise error if missing
        for data in self.required_data:
            if (missing_index := df.require_data(**data.dict())) is not None:
                error = True
                logger.error(
                    f"Required data {data} from file {get_relative_path(self.file)} "
                    f"missing for:\n{missing_index}"
                )
        if error:
            raise RequiredDataMissingError(
                "Required data missing. Please check the log for details."
            )
        return df

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:

        errors = []
        for i, data in enumerate(self.required_data):
            try:
                data.validate_with_definition(dsd)
            except ValueError as ve:
                errors.append(
                    ErrorWrapper(
                        ve,
                        (
                            f"In file {get_relative_path(self.file)}\n"
                            f"entry nr. {i+1}"
                        ),
                    )
                )
        if errors:
            raise pydantic.ValidationError(errors, model=self.__class__)
