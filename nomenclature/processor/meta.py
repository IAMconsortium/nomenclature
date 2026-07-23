import logging
import textwrap
import pandas as pd
import pyam
import yaml

from typing import Any
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pyam import IamDataFrame
from pyam.utils import adjust_log_level
from nomenclature.definition import DataStructureDefinition
from nomenclature.codelist import MetaCodeList
from nomenclature.exceptions import MetaValidationError
from nomenclature.processor import Validator
from nomenclature.processor.validator import (
    ValidationBounds,
    ValidationRange,
    ValidationValue,
    ValidationItem,
    WarningEnum,
)
from nomenclature.utils import get_relative_path
from toolkit.exceptions import NoTracebackException, NoTracebackExceptionGroup

logger = logging.getLogger(__name__)


class MetaFilter(BaseModel):
    meta: list[str] = Field(..., alias="meta_column_to_validate")

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )

    @field_validator("meta", mode="after")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    @property
    def criteria(self):
        return self.model_dump(exclude_none=True, exclude_unset=True)

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        """Check meta indicators to validate against the DataStructureDefinition"""
        codelist: MetaCodeList | None = getattr(dsd, "meta", None)
        # No validation if codelist is not defined or filter-item is None
        if codelist is None or getattr(self, "meta") is None:
            return
        if invalid := codelist.validate_items(getattr(self, "meta")):
            if errors := NoTracebackException(
                "The following meta indicators are not defined in the "
                "DataStructureDefinition:\n   "
                + ", ".join(f"'{item}'" for item in invalid)
            ):
                raise NoTracebackExceptionGroup(
                    f"Errors in {self.__class__.__name__}", errors
                )


class MetaValidationValue(ValidationValue):
    value: list[Any] = Field(..., alias="values")

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )

    @field_validator("value", mode="after")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]


class MetaValidationItem(ValidationItem, MetaFilter):
    """Validation item for meta indicator validation"""

    validation: list[MetaValidationValue | ValidationBounds | ValidationRange]

    def apply(self, df: IamDataFrame, fail_list: list, output_list: list):
        """Apply meta validation to IamDataFrame."""
        error = False
        per_item_df = df.meta.filter(self.meta, axis="columns")

        # If name is given, set a meta indicator for the item being processed
        if self.name is not None:
            meta_index = per_item_df.index.copy()
            per_item_df[self.name] = "ok"

        for criterion in self.validation:
            failed_validation = _validate_meta(per_item_df, **criterion.validation_args)
            if failed_validation is not None:
                # Create a new meta DataFrame with failed validation rows removed
                per_item_df = pd.concat(
                    [per_item_df, failed_validation]
                ).drop_duplicates(keep=False)

                # Mark failing scenarios with a meta indicator and warning level
                failed_index = failed_validation.set_index(
                    ["model", "scenario"]
                ).index.drop_duplicates()

                if self.name is not None:
                    df[self.name].iloc[failed_index] = criterion.warning_level.name
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


class MetaValidator(Validator):
    """Meta indicator validation and processing class"""

    criteria_items: list[MetaValidationItem]
    file: Path | str
    output_path: Path | None = None
    exception_cls: type[NoTracebackException] = MetaValidationError

    def _values_allowed(self, values, allowed_values, meta_indicator) -> bool:
        """Checks if the values within a meta indicator column are
        listed in model mapping

        Parameters
        ----------
        values :
            List of values in the meta_indicator column of the df: IamDataFrame.
        allowed_values :
            List of allowed values for the meta_indicator column
        meta_indicator :
            The name of the meta_indicator/column whose values are being checked.

        Returns
        -------
        True : boolean
            If all column elements are listed in model mapping

        Raises
        ------
        ValueError
            *If any of the values in the meta indicator column are not
            listed in model mapping


        """
        not_allowed = [value for value in values if value not in allowed_values]
        if not_allowed:
            raise ValueError(
                f"Invalid value for meta indicator '{meta_indicator}': {repr_list(not_allowed)}\n"
                f"Allowed values: {repr_list(allowed_values)}"
            )
        return True

    @classmethod
    def from_file(
        cls, file: Path | str, output_path: Path | str | None = None
    ) -> "MetaValidator":
        """Create a :class:`MetaValidator` from a YAML file.

        Parameters
        ----------
        file : :class:`pathlib.Path` or str
            Path to the YAML file containing the validation criteria.
        output_path : :class:`pathlib.Path` or str, optional
            Path to write an Excel file with all flagged datapoints.

        Returns
        -------
        MetaValidator
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
                if criterion not in ["name", "meta", "validation"]
            ]
            for criterion in criteria:
                value = item.pop(criterion)
                for criteria_item in item["validation"]:
                    criteria_item[criterion] = value
            criteria_items.append(item)

        return cls(file=file, criteria_items=criteria_items, output_path=output_path)  # type: ignore

    @classmethod
    def from_codelist(
        cls, codelist: MetaCodeList, output_path: Path | None = None
    ) -> "MetaValidator":
        """Create a MetaValidator from a MetaCodeList

        Parameters
        ----------
        codelist : MetaCodeList
            The MetaCodeList to use for validation

        Returns
        -------
        MetaValidator
            A new MetaValidator instance with the given MetaCodeList
        """
        criteria_items = [
            {
                "meta": [meta.name],
                "validation": [meta.validation_args],
            }
            for meta in codelist.values()
            if meta.has_validation_args
        ]
        return cls(
            criteria_items=criteria_items, file="definitions", output_path=output_path
        )

    def apply(self, df: pyam.IamDataFrame) -> pyam.IamDataFrame:
        """Apply meta indicator validation processing

        Parameters
        ----------
        df (pyam.IamDataFrame)
            Input data whose meta indicators will be validated

        Returns
        -------
        df (pyam.IamDataFrame)
            If all meta indicators and their values are listed in the
            model mapping, the same df is returned.

        Raises
        ------
        ValueError
            *If a meta indicator in the 'df' is not listed in the .yaml
            definition file
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
                raise MetaValidationError(fail_list, self.file)
            if fail_list:
                fail_msg = (
                    "Meta validation with warning(s) " + fail_msg + "\n".join(fail_list)
                )
                logger.warning(fail_msg)
        return df

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors: list[Exception] = []
        for criterion in self.criteria_items:
            try:
                criterion.validate_with_definition(dsd)
            except NoTracebackExceptionGroup as exception:
                errors.extend(exception.exceptions)
        if errors:
            raise NoTracebackExceptionGroup(
                f"Error in MetaValidator (file {get_relative_path(self.file)})",
                errors,
            )


def repr_list(x):
    return "'" + "', '".join(map(str, x)) + "'"


def _validate_meta(df: pd.DataFrame, **kwargs) -> pd.DataFrame | None:
    """Validate meta indicator values in IamDataFrame.

    Parameters
    ----------
    df : IamDataFrame
        Input data whose meta indicators will be validated
    **kwargs : dict
        Validation criteria

    Returns
    -------
    pd.DataFrame | None
        A DataFrame of failing scenarios if any, otherwise None

    Raises
    ------
    ValueError
        *If a meta indicator in the 'df' is not listed in the .yaml
        definition file
    """
    _df = df.copy()
    value = kwargs.get("value")
    upper_bound = kwargs.get("upper_bound")
    lower_bound = kwargs.get("lower_bound")
    if df.empty:
        logger.warning("No data matches filters, skipping validation.")
        return

    failed_validation: list[pd.DataFrame] = []
    if value is not None:
        failed_validation.append(_df[~_df.isin(value)])
    if upper_bound is not None:
        failed_validation.append(_df[_df > upper_bound])
    if lower_bound is not None:
        failed_validation.append(_df[_df < lower_bound])
    if not failed_validation:
        return
    _df = pd.concat(failed_validation).sort_index()

    if not _df.empty:
        msg = "{} of {} meta indicators do not satisfy the criteria"
        logger.warning(msg.format(len(_df), len(df)))
        return _df.reset_index()
