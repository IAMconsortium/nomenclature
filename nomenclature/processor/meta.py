import logging
import pyam
import yaml

from typing import Any
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from nomenclature.definition import DataStructureDefinition
from nomenclature.codelist import MetaCodeList
from nomenclature.processor import Validator
from nomenclature.processor.validator import (
    ValidationBounds,
    ValidationRange,
    ValidationValue,
    ValidationItem,
)
from nomenclature.utils import get_relative_path
from toolkit.exceptions import NoTracebackException, NoTracebackExceptionGroup

logger = logging.getLogger(__name__)


class MetaFilter(BaseModel):
    meta: str = Field(..., alias="meta_column_to_validate")

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )

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


class MetaValidationItem(ValidationItem, MetaFilter):
    """Validation item for meta indicator validation"""

    validation: list[MetaValidationValue | ValidationBounds | ValidationRange]

    @property
    def filter_args(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["validation", "name"]
        )

    def apply(df):
        pass


class MetaValidator(Validator):
    """Meta indicator validation and processing class"""

    criteria_items: list[MetaValidationItem]
    file: Path | str
    output_path: Path | None = None

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
                "meta": meta.name,
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

        if invalid_meta_indicators := [
            meta_indicator
            for meta_indicator in df.meta.columns
            if meta_indicator not in self.meta_code_list.mapping
        ]:
            raise ValueError(
                f"Invalid meta indicator: {repr_list(invalid_meta_indicators)}\n"
                f"Valid meta indicators: {repr_list(self.meta_code_list.mapping.keys())}"
            )

        for meta_indicator in df.meta.columns:
            self._values_allowed(
                list(set(df.meta[meta_indicator].values)),
                self.meta_code_list.mapping[meta_indicator].allowed_values,
                meta_indicator,
            )
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
                f"Error in DataValidator (file {get_relative_path(self.file)})",
                errors,
            )


def repr_list(x):
    return "'" + "', '".join(map(str, x)) + "'"
