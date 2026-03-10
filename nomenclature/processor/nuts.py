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
                # Remove NUTS3, add aggregated NUTS2
                _df = _df.filter(region=nuts3_in_data, keep=False)
                _df = pyam.concat([_df, IamDataFrame(pd.concat(_processed_data))])

            # NUTS2 > NUTS1 aggregation (uses original NUTS2 + aggregated NUTS2)
            if nuts2_in_data := (set(_df.region) & {r.code for r in nuts.get(level=2)}):
                _processed_data = self._aggregate_nuts_level(_df, nuts2_in_data, 3)
                # Remove NUTS2, add aggregated NUTS1
                _df = _df.filter(region=nuts2_in_data, keep=False)
                _df = pyam.concat([_df, IamDataFrame(pd.concat(_processed_data))])

            # NUTS1 > Country aggregation (uses original NUTS1 + aggregated NUTS1)
            if nuts1_in_data := (set(_df.region) & {r.code for r in nuts.get(level=1)}):
                _processed_data = self._aggregate_nuts_level(_df, nuts1_in_data, 2)

            # Compare & merge with pre-aggregated data
            _data, difference = merge_with_preaggregated_data(
                model_df,
                _processed_data,
                countries.names,
                self.variable_codelist,
                rtol_difference,
                return_aggregation_difference,
                model,
            )

        return IamDataFrame(_data, meta=model_df.meta), difference
