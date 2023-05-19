import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import pydantic
import yaml
import pyam
from pyam import IamDataFrame
from pydantic import BaseModel, validator, root_validator, Field
from pydantic.error_wrappers import ErrorWrapper

from nomenclature.definition import DataStructureDefinition
from nomenclature.error.required_data import RequiredDataMissingError
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class RequiredMeasurand(BaseModel):
    variable: str
    unit: List[Union[str, None]] = Field(...)

    @validator("unit", pre=True)
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]


class RequiredData(BaseModel):
    measurand: Optional[List[RequiredMeasurand]]
    variable: Optional[List[str]]
    region: Optional[List[str]]
    year: Optional[List[int]]

    @validator("measurand", "region", "year", "variable", pre=True)
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    @root_validator(pre=True)
    def check_variable_measurand_collision(cls, values):
        if values.get("measurand") and values.get("variable"):
            raise ValueError("'measurand' and 'variable' cannot be used together.")
        return values

    @root_validator(pre=True)
    def check_variable_measurand_neither(cls, values):
        if values.get("measurand") is None and values.get("variable") is None:
            raise ValueError("Either 'measurand' or 'variable' must be given.")
        return values

    @validator("measurand", pre=True, each_item=True)
    def cast_to_RequiredMeasurand(cls, v):
        if len(v) != 1:
            raise ValueError("Measurand must be a single value dictionary")
        variable = next(iter(v))
        return RequiredMeasurand(variable=variable, **v[variable])

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        error_msg = ""

        # check for undefined regions and variables
        for dimension, attribute_name in (
            ("region", "region"),
            ("variable", "variables"),
        ):
            if invalid := getattr(dsd, dimension).validate_items(
                getattr(self, attribute_name) or []
            ):
                error_msg += (
                    f"The following {dimension}(s) were not found in the "
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
    def variables(self) -> List[str]:
        if self.measurand is not None:
            return [m.variable for m in self.measurand]
        return self.variable

    @property
    def pyam_required_data_list(self) -> List[List[dict]]:
        if self.measurand is not None:
            return [
                [
                    {
                        "region": self.region,
                        "year": self.year,
                        "variable": measurand.variable,
                        "unit": unit,
                    }
                    for unit in measurand.unit
                ]
                for measurand in self.measurand
            ]
        return [
            [
                {
                    "region": self.region,
                    "year": self.year,
                    "variable": variable,
                }
            ]
            for variable in self.variable
        ]

    def _wrong_unit_variables(
        self, dsd: DataStructureDefinition
    ) -> List[Tuple[str, str, str]]:
        wrong_units: List[Tuple[str, Any, Any]] = []
        if hasattr(dsd, "variable") and self.measurand is not None:
            wrong_units.extend(
                (m.variable, unit, dsd.variable[m.variable].unit)
                for m in self.measurand
                for unit in m.unit
                if m.variable in dsd.variable  # check if the variable exists
                and unit not in dsd.variable[m.variable].units
            )

        return wrong_units


class RequiredDataValidator(Processor):
    description: Optional[str]
    model: Optional[List[str]]
    required_data: List[RequiredData]
    file: Path

    @validator("model", pre=True)
    def convert_to_list(cls, v):
        return pyam.utils.to_list(v)

    @classmethod
    def from_file(cls, file: Union[Path, str]) -> "RequiredDataValidator":
        with open(file, "r") as f:
            content = yaml.safe_load(f)
        return cls(file=file, **content)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        if self.model is not None:
            models_to_check = [model for model in df.model if model in self.model]
        else:
            models_to_check = df.model
        error = any(
            self.check_required_data_per_model(df, model) for model in models_to_check
        )
        if error:
            raise RequiredDataMissingError(
                "Required data missing. Please check the log for details."
            )
        return df

    def check_required_data_per_model(self, df: IamDataFrame, model: str) -> bool:
        per_model_data = df.filter(model=model)
        error = False
        for data in self.required_data:
            for requirements in data.pyam_required_data_list:
                if all(
                    (missing_index := per_model_data.require_data(**requirement))
                    is not None
                    for requirement in requirements
                ):
                    error = True
                    logger.error(
                        f"Required data {requirements} from file "
                        f"{get_relative_path(self.file)} missing for:\n"
                        f"{missing_index}"
                    )
        return error

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors = []
        for i, data in enumerate(self.required_data):
            try:
                data.validate_with_definition(dsd)
            except ValueError as value_error:
                errors.append(
                    ErrorWrapper(
                        value_error,
                        (
                            f"In file {get_relative_path(self.file)}\n"
                            f"entry nr. {i+1}"
                        ),
                    )
                )
        if errors:
            raise pydantic.ValidationError(errors, model=self.__class__)
