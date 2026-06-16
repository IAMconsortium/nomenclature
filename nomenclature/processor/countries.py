import logging
import pyam
import pandas as pd

from pathlib import Path
from pyam import IamDataFrame
from pyam.utils import adjust_log_level
from pydantic import ConfigDict

from nomenclature.codelist import VariableCodeList, RegionCodeList
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import Processor
from nomenclature.processor.region import (
    aggregate_region_with_variable_rules,
    merge_with_preaggregated_data,
)
from nomenclature.exceptions import UnknownRegionError
from nomenclature.countries import countries

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


class CountryProcessor(Processor):
    """Country to regional aggregation (R5/R9/R10) for scenario processing.

    Aggregates country-level data to standard regional groupings (R5, R9, R10)
    as defined in the region codelist (typically imported from common-definitions).

    The processor looks for regions with hierarchy "R5", "R9", or "R10" in the
    region codelist and uses their `countries` attribute to perform aggregation.
    """

    variable_codelist: VariableCodeList
    region_codelist: RegionCodeList
    models: list[str]

    model_config = ConfigDict(hide_input_in_errors=True)

    @classmethod
    def from_definition(
        cls,
        dsd: DataStructureDefinition,
        models: list[str] | None = None,
    ):
        """Instantiate from a :class:`DataStructureDefinition`.

        Parameters
        ----------
        dsd : DataStructureDefinition
            Project data structure definition.
        models : list[str], optional
            Models for which to apply country aggregation. Defaults to the list configured
            under ``config.processor.countries`` in *dsd*.

        Raises
        ------
        ValueError
            If no models are configured for country processing.
        """
        models = models or dsd.config.processor.country
        if not models:
            raise ValueError("No models configured for Country processor")
        return cls(
            variable_codelist=dsd.variable,
            region_codelist=dsd.region,
            models=models,
        )

    @property
    def regional_aggregates_by_level(self) -> dict[str, dict[str, list[str]]]:
        """Return regional aggregates grouped by hierarchy level."""
        aggregates_by_level: dict[str, dict[str, list[str]]] = {}
        for code in self.region_codelist.mapping.values():
            # Check if this is a regional aggregate (R5/R9/R10)
            hierarchy = code.hierarchy or ""
            level = next(
                (pattern for pattern in ["R5", "R9", "R10"] if pattern in hierarchy),
                None,
            )
            if level:
                # Get constituent countries (except for "Other" regions)
                if not code.countries and not code.name.startswith("Other"):
                    raise ValueError(
                        f"List of constituent countries for region '{code.name}' "
                        "not found in codelist."
                    )
                constituent_countries = code.countries

                if constituent_countries:
                    aggregates_by_level.setdefault(level, {})[code.name] = (
                        constituent_countries
                    )

        return aggregates_by_level

    @property
    def regional_aggregates(self) -> dict[str, list[str]]:
        """Return mapping of regional aggregate names to constituent country names.

        Looks for regions in the codelist with hierarchy "R5", "R9", or "R10"
        and extracts constituent countries from `countries` or `iso3_codes` attributes.

        These regions are typically imported from the common-definitions repository.

        Returns
        -------
        dict[str, list[str]]
            Mapping of region name to list of constituent country names.
        """
        aggregates = {}
        for level_aggregates in self.regional_aggregates_by_level.values():
            aggregates.update(level_aggregates)

        return aggregates

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Apply country to regional aggregation.

        Parameters
        ----------
        df : IamDataFrame
            Input data to be aggregated.

        Returns
        -------
        IamDataFrame
            Aggregated data with country-level data and aggregated regional data.

        Raises
        ------
        UnknownRegionError
            If the result contains regions not defined in the region codelist.
        """
        processed_dfs: list[IamDataFrame] = []

        for model in df.model:
            model_df = df.filter(model=model)

            # Skip unlisted models
            if model not in self.models:
                processed_dfs.append(model_df)
            else:
                logger.info(f"Applying country processing for model '{model}'")
                processed_dfs.append(self._apply_country_processing(model_df)[0])

        res = pyam.concat(processed_dfs)
        if not_defined_regions := self.region_codelist.validate_items(res.region):
            raise UnknownRegionError(not_defined_regions)

        return res

    def _apply_country_processing(
        self,
        model_df: IamDataFrame,
        return_aggregation_difference: bool = False,
        rtol_difference: float = 0.01,
    ):
        """Apply the full country aggregation pipeline for a single model.

        Parameters
        ----------
        model_df : IamDataFrame
            Data for a single model.
        return_aggregation_difference : bool, optional
            Whether to return aggregation differences for diagnostics.
        rtol_difference : float, optional
            Relative tolerance used when comparing pre-aggregated regional data
            against freshly aggregated values.

        Returns
        -------
        tuple[IamDataFrame, Any]
            Processed data and (optionally populated) aggregation difference.
        """
        model = model_df.model[0]
        _df = model_df.copy()

        # Get regional aggregation mappings from codelist
        regional_aggregates_by_level = self.regional_aggregates_by_level

        if not regional_aggregates_by_level:
            logger.warning(
                f"No regional aggregates (R5/R9/R10) found in region codelist "
                f"for model '{model}'. Ensure R5/R9/R10 regions are defined in "
                "the region codelist (e.g., imported from common-definitions)."
            )
            return _df, pd.DataFrame()

        merged_data = []
        differences = []

        # Silence pyam's empty filter warnings
        with adjust_log_level(logger="pyam", level="ERROR"):
            for level, regional_aggregates in regional_aggregates_by_level.items():
                level_aggregated_data = []
                target_regions = list(regional_aggregates.keys())

                for region_name, constituent_countries in regional_aggregates.items():
                    # Check if constituent countries exist in the data
                    available_countries = set(_df.region) & set(constituent_countries)

                    if not available_countries:
                        logger.debug(
                            f"No data for constituent countries of '{region_name}' "
                            f"in model '{model}'"
                        )
                        continue

                    logger.info(
                        f"Aggregating {len(available_countries)} countries "
                        f"to '{region_name}'"
                    )

                    # Aggregate using variable-specific rules
                    aggregated = aggregate_region_with_variable_rules(
                        _df,
                        region_name,
                        sorted(available_countries),
                        self.variable_codelist,
                    )
                    level_aggregated_data.extend(aggregated)

                pre_aggregated_level_df = model_df.filter(
                    region=target_regions,
                    variable=self.variable_codelist,
                )

                if not level_aggregated_data and pre_aggregated_level_df.empty:
                    logger.info(
                        f"Skipping country aggregation for hierarchy '{level}' "
                        f"in model '{model}' (no matching data or pre-aggregated regions)"
                    )
                    continue

                level_data, difference = merge_with_preaggregated_data(
                    model_df,
                    level_aggregated_data,
                    target_regions,
                    self.variable_codelist,
                    rtol_difference,
                    return_aggregation_difference,
                    model,
                )
                merged_data.append(level_data)
                if not difference.empty:
                    differences.append(difference)

            if merged_data:
                _data = pd.concat(merged_data)
            else:
                _data = pd.DataFrame()

            # Include all country-level data
            country_names = set(countries.names)
            if countries_to_keep := set(_df.region) & country_names:
                _data = pd.concat(
                    [_data, _df.filter(region=list(countries_to_keep))._data]
                )

        difference = pd.concat(differences) if differences else pd.DataFrame()

        return IamDataFrame(_data, meta=model_df.meta), difference
