import logging
import pyam

from pathlib import Path

from pydantic import ConfigDict, Field
from nomenclature.processor import Processor
from nomenclature.codelist import MetaCodeList
from nomenclature.processor.validator import ValidationValue, ValidationItem

logger = logging.getLogger(__name__)


class MetaValidationValue(ValidationValue):
    value: list[str] = Field(..., alias="values")

    config_dict = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )


class MetaValidationItem(ValidationItem):
    """Validation item for meta indicator validation"""

    meta_column_to_validate: str = Field(..., alias="meta")

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )

    @property
    def filter_args(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, exclude=["validation", "name"]
        )

    def apply(df):
        pass


class MetaValidator(Processor):
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


def repr_list(x):
    return "'" + "', '".join(map(str, x)) + "'"
