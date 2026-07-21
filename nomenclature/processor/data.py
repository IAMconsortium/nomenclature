import logging
import textwrap
from enum import IntEnum
from pathlib import Path

import pandas as pd
from pydantic import computed_field
import yaml
from pyam import IamDataFrame
from pyam.utils import adjust_log_level

from nomenclature.codelist import VariableCodeList
from nomenclature.definition import DataStructureDefinition
from nomenclature.exceptions import DataValidationError, NoTracebackExceptionGroup
from nomenclature.processor.validator import (
    ValidationValue,
    ValidationRange,
    ValidationBounds,
    ValidationItem,
)
from nomenclature.processor import Processor
from nomenclature.processor.iamc import IamcDataFilter
from nomenclature.utils import get_relative_path

logger = logging.getLogger(__name__)


class WarningEnum(IntEnum):
    error = 50
    high = 40
    medium = 30
    low = 20


class DataValidationValue(ValidationValue):
    value: float
    rtol: float = 0.0
    atol: float = 0.0

    @property
    def tolerance(self) -> float | None:
        return (
            self.value * self.rtol + self.atol
            if isinstance(self.value, float)
            else None
        )

    @computed_field
    def upper_bound(self) -> float | None:
        return self.value + self.tolerance

    @computed_field
    def lower_bound(self) -> float | None:
        return self.value - self.tolerance

    @property
    def validation_args(self):
        if isinstance(self.value, list):
            return {"value": self.value}
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


class DataValidationItem(ValidationItem, IamcDataFilter):
    validation: list[DataValidationValue | ValidationBounds | ValidationRange]

    @property
    def filter_args(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["validation", "name"]
        )

    def apply(
        self, df: IamDataFrame, fail_list: list, output_list: list
    ) -> tuple[bool, list, list]:
        """Apply data validation to IamDataFrame."""
        error = False
        per_item_df = df.filter(**self.filter_args)

        # If name is given, set a meta indicator for the item being processed
        if self.name is not None:
            meta_index = per_item_df.index.copy()
            df.set_meta(name=self.name, meta="ok", index=meta_index)

        for criterion in self.validation:
            failed_validation = per_item_df.validate(**criterion.validation_args)
            if failed_validation is not None:
                per_item_df = IamDataFrame(
                    pd.concat([per_item_df.data, failed_validation]).drop_duplicates(
                        keep=False
                    )
                )

                # Mark failing scenarios with a meta indicator and warning level
                failed_index = failed_validation.set_index(
                    ["model", "scenario"]
                ).index.drop_duplicates()

                if self.name is not None:
                    df.set_meta(
                        name=self.name,
                        meta=criterion.warning_level.name,
                        index=meta_index.intersection(failed_index),
                    )
                    # Remove failed scenarios from the meta index to avoid
                    # lower warnings overriding higher warnings in meta indicators
                    meta_index = meta_index.difference(failed_index)

                failed_validation["warning_level"] = criterion.warning_level.name
                failed_validation["criteria"] = str(criterion)
                output_list.append(failed_validation)
                if criterion.warning_level == WarningEnum.error:
                    error = True
                fail_list.append("  Criteria: " + str(self) + ", " + str(criterion))
                fail_list.append(
                    textwrap.indent(
                        failed_validation.iloc[:, :-1].to_string(), prefix="  "
                    )
                    + "\n"
                )
        return error, fail_list, output_list


class DataValidator(Processor):
    """Processor for validating IAMC datapoints"""

    criteria_items: list[DataValidationItem]
    file: Path | str
    output_path: Path | None = None

    @classmethod
    def from_file(
        cls, file: Path | str, output_path: Path | str | None = None
    ) -> "DataValidator":
        """Create a :class:`DataValidator` from a YAML file.

        Parameters
        ----------
        file : :class:`pathlib.Path` or str
            Path to the YAML file containing the validation criteria.
        output_path : :class:`pathlib.Path` or str, optional
            Path to write an Excel file with all flagged datapoints.

        Returns
        -------
        DataValidator
        """
        with open(file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        criteria_items = []
        for item in content:
            # Simple case where filter and criteria args are all given at top level
            if "validation" not in item:
                item["validation"] = [dict()]

            # If some criteria args are given at top-level, add to "validation" list
            criteria = [
                criterion
                for criterion in item
                if criterion
                not in list(IamcDataFilter.model_fields) + ["name", "validation"]
            ]
            for criterion in criteria:
                value = item.pop(criterion)
                for criteria_item in item["validation"]:
                    criteria_item[criterion] = value
            criteria_items.append(item)

        return cls(file=file, criteria_items=criteria_items, output_path=output_path)  # type: ignore

    @classmethod
    def from_codelist(
        cls, codelist: VariableCodeList, output_path: Path | None = None
    ) -> "DataValidator":
        """Create a :class:`DataValidator` from a :class:`~nomenclature.codelist.VariableCodeList`.

        Extracts validation criteria from variables in the codelist that define
        bounds or tolerance ranges.

        Parameters
        ----------
        codelist : VariableCodeList
            Variable codelist containing validation arguments.
        output_path : :class:`pathlib.Path`, optional
            Path to write an Excel file with all flagged datapoints.

        Returns
        -------
        DataValidator
        """
        criteria_items = [
            {
                "variable": variable.name,
                "validation": [variable.validation_args],
            }
            for variable in codelist.values()
            if variable.has_validation_args
        ]
        return cls(
            file="definitions", criteria_items=criteria_items, output_path=output_path
        )

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Validates data in IAMC format according to specified criteria.

        Logs warning/error messages for each criterion that is not met.

        Parameters
        ----------
        df : pyam.IamDataFrame
            Data in IAMC format to be validated

        Returns
        -------
        pyam.IamDataFrame

        Raises
        ------
            :exc:`ValueError` if any criterion has a warning level of ``error``
        """

        error_list: list[bool] = []
        fail_list: list[str] = []
        output_list: list[pd.DataFrame] = []

        with adjust_log_level():
            for item in self.criteria_items:
                error, fail_list, output_list = item.apply(df, fail_list, output_list)
                error_list.append(error)
            if self.output_path:
                pd.concat(output_list).to_excel(self.output_path, index=False)
            fail_msg = f"(file {get_relative_path(self.file)}):\n"
            if any(error_list):
                raise DataValidationError(fail_list, self.file)
            if fail_list:
                fail_msg = (
                    "Data validation with warning(s) " + fail_msg + "\n".join(fail_list)
                )
                logger.warning(fail_msg)
        return df

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        """Validate the criteria items against a :class:`DataStructureDefinition`.

        Checks that all variables and regions referenced in the criteria
        exist in the provided definition.

        Parameters
        ----------
        dsd : DataStructureDefinition
            Data structure definition to validate against.

        Raises
        ------
        ExceptionGroup
            If any criteria item references unknown variables or regions.
        """
        errors: list[Exception] = []
        for criterion in self.criteria_items:
            try:
                criterion.validate_with_definition(dsd)
            except NoTracebackExceptionGroup as exception:
                errors.extend(exception.exceptions)
        if errors:
            raise NoTracebackExceptionGroup(
                f"Error in DataValidator (file {get_relative_path(self.file)})",
                errors,
            )
