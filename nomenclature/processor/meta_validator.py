import logging
import textwrap
import pandas as pd
import pyam
import yaml

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
from nomenclature.utils import get_relative_path, single_input_to_list
from toolkit.exceptions import NoTracebackException, NoTracebackExceptionGroup

logger = logging.getLogger(__name__)


class MetaFilter(BaseModel):
    meta: list[str] = Field(..., alias="meta_columns_to_validate")

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )

    @field_validator("meta", mode="before")
    @classmethod
    def cast_single_input_to_list(cls, v):
        return single_input_to_list(v)

    @property
    def filter_args(self):
        return self.model_dump(
            exclude_none=True, exclude_unset=True, include=set(MetaFilter.model_fields)
        )

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        """Check criteria items against the DataStructureDefinition."""
        codelist: MetaCodeList | None = getattr(dsd, "meta", None)
        # No validation if codelist is not defined or filter-item is None
        if codelist is None:
            return
        if invalid := codelist.validate_items(getattr(self, "meta")):
            raise NoTracebackException(
                "The following meta-indicators are not defined in the "
                "MetaCodeList:\n   " + ", ".join(f"'{item}'" for item in invalid)
            )


class MetaValidationValue(ValidationValue):
    value: float | str | list[float | str] = Field(..., alias="values")
    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="forbid"
    )

    @field_validator("value", mode="after")
    @classmethod
    def coerce_str_to_list_str(cls, v):
        if isinstance(v, (float, list)):
            return v
        if isinstance(v, str):
            return [v]


class MetaValidationItem(ValidationItem, MetaFilter):
    """Validation item for meta-indicator validation."""

    validation: list[MetaValidationValue | ValidationBounds | ValidationRange]

    def apply(self, df: IamDataFrame, fail_list: list, output_list: list):
        """Apply meta validation to IamDataFrame."""
        error = False
        per_item_df = df.meta.filter(self.meta, axis="columns")

        # If name is given, set a meta-indicator for the item being processed
        if self.name is not None:
            meta_index: pd.MultiIndex = per_item_df.index
            df.set_meta(name=self.name, meta="ok", index=meta_index)

        for criterion in self.validation:
            failed_validation = self._validate_meta(
                per_item_df, **criterion.validation_args
            )
            if failed_validation is not None:
                # Create a new meta DataFrame with failed validation rows removed
                per_item_df = per_item_df.loc[
                    ~per_item_df.index.isin(failed_validation.index)
                ]

                # Mark failing scenarios with a meta-indicator and warning level
                failed_index: pd.MultiIndex = failed_validation.index.drop_duplicates()

                if self.name is not None:
                    df.meta.loc[failed_index.values, self.name] = (
                        criterion.warning_level.name
                    )
                    # Remove failed scenarios from the meta index to avoid
                    # lower warnings overriding higher warnings in meta-indicators
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

    @staticmethod
    def _validate_meta(
        df: pd.DataFrame,
        value: float | str | list[float | str] | None = None,
        upper_bound: float | None = None,
        lower_bound: float | None = None,
    ) -> pd.DataFrame | None:
        """Validate meta-indicator values in IamDataFrame.

        Parameters
        ----------
        df : IamDataFrame
            Input data whose meta-indicators will be validated
        value : float | str | list[float | str], optional
            The value(s) to validate against
        upper_bound : float, optional
            The upper bound for the validation
        lower_bound : float, optional
            The lower bound for the validation

        Returns
        -------
        pd.DataFrame | None
            A DataFrame of failing scenarios if any, otherwise None
        """
        if df.empty:
            column_name = "', '".join(df.columns)
            logger.warning(
                f"Columns '{column_name}' do not exist in `meta`, skipping validation."
            )
            return
        _df = df.copy()

        failed_index = set()
        if value is not None:
            failed_index.update(_df[~_df.isin(value)].dropna(how="all").index)
        if upper_bound is not None:
            failed_index.update(_df[_df > upper_bound].dropna(how="all").index)
        if lower_bound is not None:
            failed_index.update(_df[_df < lower_bound].dropna(how="all").index)
        if not failed_index:
            return
        _df = df.loc[sorted(failed_index)]

        if not _df.empty:
            return _df
        return None

    def __str__(self):
        return ", ".join([f"{key}: {value}" for key, value in self.filter_args.items()])


class MetaValidator(Validator):
    """Meta-indicator validation and processing class."""

    criteria_items: list[MetaValidationItem]
    exception_cls: type[NoTracebackException] = MetaValidationError

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
            if "validation" not in item:
                raise ValueError(
                    "Each meta-indicator validation item must define a 'validation' field."
                )
            if disallowed := set(item) - {"name", "meta", "validation"}:
                raise ValueError(
                    "Meta-indicator validation criteria must be defined inside 'validation': "
                    + ", ".join(sorted(disallowed))
                )
            criteria_items.append(item)

        return cls(file=file, criteria_items=criteria_items, output_path=output_path)  # type: ignore

    def apply(self, df: pyam.IamDataFrame) -> pyam.IamDataFrame:
        """Apply meta-indicator validation to IamDataFrame.

        Logs warning/error messages for each criterion that is not met.

        Parameters
        ----------
        df : pyam.IamDataFrame
            Input data whose meta-indicators will be validated

        Returns
        -------
        pyam.IamDataFrame
            A DataFrame with new meta columns with validation results
            (as specified in the validation criteria).

        Raises
        ------
        MetaValidationError
            If validation fails because meta-indicators are missing and/or values are wrong
        """

        error_list: list[bool] = []
        fail_list: list[str] = []
        output_list: list[pd.DataFrame] = []

        with adjust_log_level(logger="pyam", level="ERROR"):
            for item in self.criteria_items:
                error, fail_list, output_list = item.apply(df, fail_list, output_list)
                error_list.append(error)
            if output_list:
                failed_validation = pd.concat(output_list)
                unique_failed_scenarios = len(failed_validation.index.drop_duplicates())
                logger.warning(
                    f"{unique_failed_scenarios} of {len(self.criteria_items)} criteria failed validation "
                    f"({unique_failed_scenarios} of {len(df.meta)} rows)."
                )
            if self.output_path:
                pd.concat(output_list).to_excel(self.output_path, index=False)
            if any(error_list):
                raise MetaValidationError(fail_list, self.file)
            if fail_list:
                fail_msg = (
                    "Meta-indicator validation with warning(s) "
                    + f"(file {get_relative_path(self.file)}):\n"
                    + "\n".join(fail_list)
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
