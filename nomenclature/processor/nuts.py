import logging
import re
import pyam
import pandas as pd

from collections import defaultdict
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
from nomenclature.nuts import nuts

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()

# EU27 member states alpha-2 codes (ISO 3166-1), membership as of 2026
EU27_ALPHA2: frozenset[str] = frozenset(
    {
        "AT",  # Austria
        "BE",  # Belgium
        "BG",  # Bulgaria
        "CY",  # Cyprus
        "CZ",  # Czechia
        "DE",  # Germany
        "DK",  # Denmark
        "EE",  # Estonia
        "ES",  # Spain
        "FI",  # Finland
        "FR",  # France
        "GR",  # Greece
        "HR",  # Croatia
        "HU",  # Hungary
        "IE",  # Ireland
        "IT",  # Italy
        "LT",  # Lithuania
        "LU",  # Luxembourg
        "LV",  # Latvia
        "MT",  # Malta
        "NL",  # Netherlands
        "PL",  # Poland
        "PT",  # Portugal
        "RO",  # Romania
        "SE",  # Sweden
        "SI",  # Slovenia
        "SK",  # Slovakia
    }
)
# Minimum number of EU27 member countries required to aggregate to "European Union"
EU27_MIN_COUNTRIES: int = 23
# UK alpha-2 code for "European Union and United Kingdom" aggregation
UK_ALPHA2: str = "UK"


class NutsProcessor(Processor):
    """NUTS region aggregation mappings for scenario processing"""

    variable_codelist: VariableCodeList
    region_codelist: RegionCodeList
    models: list[str]

    model_config = ConfigDict(hide_input_in_errors=True)

    @classmethod
    def from_definition(cls, dsd: DataStructureDefinition):
        models = dsd.config.processor.nuts
        if not models:
            raise ValueError("No models configured for NUTS processor")
        return cls(
            variable_codelist=dsd.variable, region_codelist=dsd.region, models=models
        )

    @property
    def nuts_codelist(self):
        return RegionCodeList(
            name="NUTS",
            mapping={
                code.name: code
                for code in self.region_codelist.mapping.values()
                if re.search(r"NUTS \d regions \(2024 edition\)", code.hierarchy)
            },
        )

    def apply(self, df: IamDataFrame):
        processed_dfs: list[IamDataFrame] = []

        for model in df.model:
            model_df = df.filter(model=model)

            # Skip unlisted models
            if model not in self.models:
                logger.info(
                    f"Skipping NUTS region aggregation for model '{model}' (no region processing mapping)"
                )
                processed_dfs.append(model_df)
            else:
                logger.info(f"Applying region-processing for model '{model}'")
                processed_dfs.append(self._apply_nuts_processing(model_df)[0])

        res = pyam.concat(processed_dfs)
        if not_defined_regions := self.region_codelist.validate_items(res.region):
            raise UnknownRegionError(not_defined_regions)

        return res

    def _aggregate_nuts_level(
        self,
        model_df: IamDataFrame,
        source_regions: list[str],
        parent_prefix_length: int,
    ) -> list[pd.Series]:
        """Aggregate source NUTS regions to their parent region.

        Parameters
        ----------
        model_df : IamDataFrame
            Input data
        source_regions : list[str]
            List of NUTS region codes to aggregate
        parent_prefix_length : int
            Length of parent region code (4 for NUTS2, 3 for NUTS1, 2 for country)

        Returns
        -------
        list[pd.Series]
            Aggregated data series
        """

        aggregated_data = []

        # Group by parent region
        parent_groups = defaultdict(list)
        for source_region in source_regions:
            parent = source_region[:parent_prefix_length]
            parent_groups[parent].append(source_region)

        # Aggregate each parent from its constituents
        for parent_code, constituents in parent_groups.items():
            parent = (
                countries.get(alpha_2=parent_code).name
                if len(parent_code) == 2  # If NUTS 1 > country, use name
                else parent_code
            )
            aggregated = aggregate_region_with_variable_rules(
                model_df,
                parent,
                constituents,
                self.variable_codelist,
            )
            aggregated_data.extend(aggregated)

        return aggregated_data

    def _aggregate_to_eu27(self, df: IamDataFrame) -> list[pd.Series]:
        """Aggregate country-level data to European Union (and United Kingdom).

        Aggregation is performed if at least 23 of the 27 EU member states
        are present in `df`.
        Aggregation to EU27+UK is additionally performed if the United Kingdom
        is also present.

        Both aggregations are **only** attempted if the target region is defined in
        the project's region codelist. If either target is not defined, the
        corresponding aggregation is silently skipped.

        Parameters
        ----------
        df : IamDataFrame
            Country-level data (after NUTS aggregation).

        Returns
        -------
        list[pd.Series]
            Aggregated EU data series (empty if threshold or codelist conditions are
            not met).
        """
        eu27_names = {countries.get(alpha_2=alpha2).name for alpha2 in EU27_ALPHA2}
        uk_name = countries.get(alpha_2=UK_ALPHA2).name

        available_eu27 = eu27_names & set(df.region)
        result: list[pd.Series] = []

        if len(available_eu27) < EU27_MIN_COUNTRIES:
            return result

        if "European Union" in self.region_codelist.mapping:
            logger.info(
                f"Aggregating {len(available_eu27)} EU27 member countries "
                "to 'European Union'"
            )
            result.extend(
                aggregate_region_with_variable_rules(
                    df,
                    "European Union",
                    sorted(available_eu27),
                    self.variable_codelist,
                )
            )

        if (
            "European Union and United Kingdom" in self.region_codelist.mapping
            and uk_name in set(df.region)
        ):
            logger.info(
                "Aggregating EU27 countries + United Kingdom to 'European Union and United Kingdom'"
            )
            result.extend(
                aggregate_region_with_variable_rules(
                    df,
                    "European Union and United Kingdom",
                    sorted(available_eu27) + [uk_name],
                    self.variable_codelist,
                )
            )

        return result

    def _apply_nuts_processing(
        self,
        model_df: IamDataFrame,
        return_aggregation_difference: bool = False,
        rtol_difference: float = 0.01,
    ):
        if len(model_df.model) != 1:
            raise ValueError(
                f"Must be called for a unique model, found: {model_df.model}"
            )
        model = model_df.model[0]

        # Check for NUTS regions not listed in the configuration
        all_nuts = {r.code for r in nuts.get(level={1, 2, 3})}
        if unaccounted_nuts := (set(model_df.region) & all_nuts) - set(
            self.nuts_codelist
        ):
            raise ValueError(
                f"Did not find NUTS region(s) {unaccounted_nuts} in 'region.nuts' configuration."
            )

        _df = model_df.copy()
        _processed_data: list[pd.Series] = []

        # Silence pyam's empty filter warnings
        with adjust_log_level(logger="pyam", level="ERROR"):
            # NUTS3 > NUTS2 aggregation
            if nuts3_in_data := (set(_df.region) & {r.code for r in nuts.get(level=3)}):
                _processed_data = self._aggregate_nuts_level(_df, nuts3_in_data, 4)
                # Keep NUTS3, add aggregated NUTS2
                _df = pyam.concat([_df, IamDataFrame(pd.concat(_processed_data))])

            # NUTS2 > NUTS1 aggregation (uses original NUTS2 + aggregated NUTS2)
            if nuts2_in_data := (set(_df.region) & {r.code for r in nuts.get(level=2)}):
                _processed_data = self._aggregate_nuts_level(_df, nuts2_in_data, 3)
                # Keep NUTS2, add aggregated NUTS1
                _df = pyam.concat([_df, IamDataFrame(pd.concat(_processed_data))])

            # NUTS1 > Country aggregation (uses original NUTS1 + aggregated NUTS1)
            if nuts1_in_data := (set(_df.region) & {r.code for r in nuts.get(level=1)}):
                _processed_data = self._aggregate_nuts_level(_df, nuts1_in_data, 2)

            # Compare & merge country-level aggregated data with any pre-aggregated
            # country data in the original model input
            _data, difference = merge_with_preaggregated_data(
                model_df,
                _processed_data,
                countries.names,
                self.variable_codelist,
                rtol_difference,
                return_aggregation_difference,
                model,
            )

            # EU27(+UK) aggregation from country-level data
            _country_df = IamDataFrame(_data, meta=model_df.meta)
            if eu_target_regions := [
                r
                for r in ("European Union", "European Union & United Kingdom")
                if r in self.region_codelist.mapping
            ]:
                _eu_aggregated = self._aggregate_to_eu27(_country_df)
                if _eu_aggregated:
                    _eu_data, _ = merge_with_preaggregated_data(
                        model_df,
                        _eu_aggregated,
                        eu_target_regions,
                        self.variable_codelist,
                        rtol_difference,
                        return_aggregation_difference,
                        model,
                    )
                    _data = pd.concat([_data, _eu_data])

            # Include all NUTS regions (source + intermediate aggregated levels)
            # that are present in the configured nuts_codelist
            if nuts_to_keep := set(_df.region) & set(self.nuts_codelist.mapping):
                _data = pd.concat([_data, _df.filter(region=list(nuts_to_keep))._data])

        return IamDataFrame(_data, meta=model_df.meta), difference
