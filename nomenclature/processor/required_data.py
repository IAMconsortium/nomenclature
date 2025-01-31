import logging
from pathlib import Path
from typing import Any, Annotated

import pandas as pd
import yaml
import pyam
from pyam import IamDataFrame
from pydantic import (
    field_validator,
    model_validator,
    BaseModel,
    Field,
    BeforeValidator,
)

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import ErrorCollector
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)


class RequiredMeasurand(BaseModel):
    variable: str
    unit: list[str | None] = Field(...)

    @field_validator("unit", mode="before")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]


def cast_to_RequiredMeasurand(v) -> RequiredMeasurand:
    if isinstance(v, RequiredMeasurand):
        return v
    if len(v) != 1:
        raise ValueError("Measurand must be a single value dictionary")
    variable = next(iter(v))
    return RequiredMeasurand(variable=variable, **v[variable])


class RequiredData(BaseModel):
    measurand: (
        list[Annotated[RequiredMeasurand, BeforeValidator(cast_to_RequiredMeasurand)]]
        | None
    ) = None
    variable: list[str] | None = None
    region: list[str] | None = None
    year: list[int] | None = None
    # TODO consider merging with IamcDataFilter

    @field_validator("measurand", "region", "year", "variable", mode="before")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    @model_validator(mode="before")
    @classmethod
    def check_variable_measurand_collision(cls, values):
        if values.get("measurand") and values.get("variable"):
            raise ValueError("'measurand' and 'variable' cannot be used together.")
        return values

    @model_validator(mode="before")
    @classmethod
    def check_variable_measurand_neither(cls, values):
        if values.get("measurand") is None and values.get("variable") is None:
            raise ValueError("Either 'measurand' or 'variable' must be given.")
        return values

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
    def variables(self) -> list[str]:
        if self.measurand is not None:
            return [m.variable for m in self.measurand]
        return self.variable

    @property
    def pyam_required_data_list(self) -> list[list[dict]]:
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
    ) -> list[tuple[str, str, str]]:
        wrong_units: list[tuple[str, Any, Any]] = []
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
    """Processor for validating required dimensions in IAMC datapoints"""

    description: str | None = None
    model: list[str] | None = None
    required_data: list[RequiredData]
    file: Path

    @field_validator("model", mode="before")
    @classmethod
    def convert_to_list(cls, v):
        return pyam.utils.to_list(v)

    @classmethod
    def from_file(cls, file: Path | str) -> "RequiredDataValidator":
        with open(file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        return cls(file=file, **content)

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Validates data in IAMC format according to required models and dimensions.

        Parameters
        ----------
        df : IamDataFrame
            Data in IAMC format to be validated

        Returns
        -------
        IamDataFrame

        Raises
        ------
            `ValueError` if any required dimension is not found in the data
        """
        if self.model is not None:
            models_to_check = [model for model in df.model if model in self.model]
        else:
            models_to_check = df.model

        if missing_data := {
            model: list(self.check_required_data_per_model(df, model))
            for model in models_to_check
            if list(self.check_required_data_per_model(df, model))
        }:
            missing_data_log_info = ""
            for model, data_list in missing_data.items():
                missing_data_log_info += f"Missing for '{model}':\n"
                for data in data_list:
                    missing_data_log_info += (
                        data.to_string(
                            index=False,
                            justify="left",
                        )
                        + "\n\n"
                    )
            logger.error(
                "Missing required data.\nFile: %s\n\n%s",
                get_relative_path(self.file),
                missing_data_log_info,
            )
            raise ValueError("Required data missing. Please check the log for details.")
        return df

    def check_required_data_per_model(
        self, df: IamDataFrame, model: str
    ) -> list[pyam.IamDataFrame]:
        model_df = df.filter(model=model)
        missing_data = []
        for requirement in self.required_data:
            for variable_requirement in requirement.pyam_required_data_list:
                missing_data_per_unit = [
                    model_df.require_data(**unit_requirement)
                    for unit_requirement in variable_requirement
                ]
                if all(missing is not None for missing in missing_data_per_unit):
                    missing_data_per_variable = pd.concat(missing_data_per_unit).astype(
                        str
                    )
                    missing_data_columns = missing_data_per_variable.columns.to_list()
                    # flatten out the last dimension for presentation
                    missing_data.append(
                        missing_data_per_variable.groupby(missing_data_columns[:-1])[
                            missing_data_columns[-1]
                        ]
                        .apply(",".join)
                        .to_frame()
                        .reset_index()
                        .drop(columns=["model"])
                        .rename(columns={"year": "year(s)"})
                    )
        return missing_data

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors = ErrorCollector()
        for data in self.required_data:
            try:
                data.validate_with_definition(dsd)
            except ValueError as value_error:
                errors.append(value_error)
        if errors:
            raise ValueError(f"In file {get_relative_path(self.file)}:\n{errors}")
