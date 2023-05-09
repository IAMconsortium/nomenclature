import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import pydantic
import yaml
from pyam import IamDataFrame
from pydantic import BaseModel, Field, validator
from pydantic.error_wrappers import ErrorWrapper

from nomenclature.definition import DataStructureDefinition
from nomenclature.error.required_data import RequiredDataMissingError
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class RequiredMeasurand(BaseModel):

    variable: str
    unit: Optional[Union[str, List[str]]] = Field(...)


class RequiredData(BaseModel):

    measurand: List[RequiredMeasurand]
    region: Optional[List[str]]
    year: Optional[List[int]]

    @validator("measurand", "region", "year", pre=True)
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    @validator("measurand", pre=True, each_item=True)
    def cast_to_RequiredMeasurand(cls, v):
        if len(v) != 1:
            raise ValueError("Measurand must be a single value dictionary")
        variable = next(iter(v))
        return RequiredMeasurand(variable=variable, **v[variable])

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        error_msg = ""

        # check for undefined regions and variables
        for dim in ("region", "variable"):
            if invalid := dsd.__getattribute__(dim).validate_items(
                self.__getattribute__(dim) or []
            ):
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

    @property
    def variable(self) -> List[str]:
        return [m.variable for m in self.measurand]

    @property
    def pyam_required_data_list(self) -> List[dict]:

        return [
            {
                "region": self.region,
                "year": self.year,
                "variable": m.variable,
                "unit": m.unit,
            }
            for m in self.measurand
        ]

    def _wrong_unit_variables(
        self, dsd: DataStructureDefinition
    ) -> List[Tuple[str, str, str]]:
        wrong_units: List[Tuple[str, Any, Any]] = []
        if hasattr(dsd, "variable"):
            wrong_units.extend(
                (m.variable, m.unit, dsd.variable[m.variable].unit)
                for m in self.measurand
                if m.variable in dsd.variable  # check if the variable exists
                and m.unit not in dsd.variable[m.variable].units
            )

        return wrong_units


class RequiredDataValidator(Processor):

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
            for requirement in data.pyam_required_data_list:
                if (missing_index := df.require_data(**requirement)) is not None:
                    error = True
                    logger.error(
                        f"Required data {requirement} from file "
                        f"{get_relative_path(self.file)} missing for:\n"
                        f"{missing_index}"
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
