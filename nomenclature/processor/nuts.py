import logging
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

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


class NutsProcessor(Processor):
    """NUTS region aggregation mappings for scenario processing"""

    variable_codelist: VariableCodeList
    nuts_codelist: RegionCodeList
    models: list[str]

    model_config = ConfigDict(hide_input_in_errors=True)

    @classmethod
    def from_definition(cls, dsd: DataStructureDefinition):
        nuts_codelist = RegionCodeList(
            name="NUTS",
            mapping={
                code.name: code
                for code in dsd.region.mapping.values()
                if "NUTS" in code.hierarchy
            },
        )
        models = dsd.config.processor.nuts
        if not models:
            raise ValueError("No models configured for NUTS processor")

        return cls(
            variable_codelist=dsd.variable, nuts_codelist=nuts_codelist, models=models
        )

    @property
    def nuts3_codelist(self) -> RegionCodeList:
        """Return a RegionCodeList of NUTS 3 regions only."""
        mapping = {
            name: code
            for name, code in self.nuts_codelist.mapping.items()
            if code.hierarchy.startswith("NUTS 3")
        }
        return RegionCodeList(name="NUTS 3", mapping=mapping)

    @property
    def nuts2_codelist(self) -> RegionCodeList:
        """Return a RegionCodeList of NUTS 2 regions only."""
        mapping = {
            name: code
            for name, code in self.nuts_codelist.mapping.items()
            if code.hierarchy.startswith("NUTS 2")
        }
        return RegionCodeList(name="NUTS 2", mapping=mapping)

    @property
    def nuts1_codelist(self) -> RegionCodeList:
        """Return a RegionCodeList of NUTS 1 regions only."""
        mapping = {
            name: code
            for name, code in self.nuts_codelist.mapping.items()
            if code.hierarchy.startswith("NUTS 1")
        }
        return RegionCodeList(name="NUTS 1", mapping=mapping)

    def apply(self, df: IamDataFrame):
        # dataframe with nuts regions
        # dsd config on nuts regions

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
                # elif any(set(model_df.region) & set(self.nuts2_codelist)):
                #     processed_dfs.append(
                #         self._apply_nuts_processing(model_df, ["NUTS2", "NUTS1"])[0]
                #     )
                # elif any(set(model_df.region) & set(self.nuts1_codelist)):
                #     processed_dfs.append(
                #         self._apply_nuts_processing(model_df, ["NUTS1"])[0]
                #     )

        res = pyam.concat(processed_dfs)
        if not_defined_regions := self.nuts_codelist.validate_items(res.region):
            raise UnknownRegionError(not_defined_regions)

        return res

    def _aggregate_nuts_level(
        self,
        model_df: IamDataFrame,
        nuts_codelist: RegionCodeList,
        parent_prefix_length: int,
    ) -> list[pd.Series]:
        """Aggregate NUTS regions to their parent level.

        Parameters
        ----------
        model_df : IamDataFrame
            Input data
        nuts_codelist : RegionCodeList
            Codelist of NUTS regions (e.g., NUTS3)
        parent_prefix_length : int
            Length of parent region code (4 for NUTS2, 3 for NUTS1, 2 for country)

        Returns
        -------
        list[pd.Series]
            Aggregated data series
        """

        aggregated_data = []
        nuts_in_data = set(model_df.region) & set(nuts_codelist)

        # Group by parent region
        parent_groups = defaultdict(list)
        for source_region in nuts_in_data:
            parent = source_region[:parent_prefix_length]
            parent_groups[parent].append(source_region)

        # Aggregate each parent from its constituents
        for parent_code, constituents in parent_groups.items():
            parent = (
                countries.get(parent_code).name
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
        # nuts: list[str] = ["NUTS3", "NUTS2", "NUTS1"],
        return_aggregation_difference: bool = False,
        rtol_difference: float = 0.01,
    ):
        if len(model_df.model) != 1:
            raise ValueError(
                f"Must be called for a unique model, found: {model_df.model}"
            )
        model = model_df.model[0]

        _df = model_df.copy()
        _processed_data: list[pd.Series] = []

        # Silence pyam's empty filter warnings
        with adjust_log_level(logger="pyam", level="ERROR"):
            # NUTS3 > NUTS2 aggregation
            nuts2_aggregated = self._aggregate_nuts_level(_df, self.nuts3_codelist, 4)
            if nuts2_aggregated:
                _processed_data.extend(nuts2_aggregated)
                # Remove NUTS3, add aggregated NUTS2
                _df = _df.filter(region=list(self.nuts3_codelist), keep=False)
                _df = pyam.concat([_df, IamDataFrame(pd.concat(nuts2_aggregated))])

            # NUTS2 > NUTS1 aggregation (uses original NUTS2 + aggregated NUTS2)
            nuts1_aggregated = self._aggregate_nuts_level(_df, self.nuts2_codelist, 3)
            if nuts1_aggregated:
                _processed_data.extend(nuts1_aggregated)
                # Remove NUTS2, add aggregated NUTS1
                _df = _df.filter(region=list(self.nuts2_codelist), keep=False)
                _df = pyam.concat([_df, IamDataFrame(pd.concat(nuts1_aggregated))])

            # NUTS1 > Country aggregation (uses original NUTS1 + aggregated NUTS1)
            country_aggregated = self._aggregate_nuts_level(_df, self.nuts1_codelist, 2)
            if country_aggregated:
                _processed_data.extend(country_aggregated)

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
