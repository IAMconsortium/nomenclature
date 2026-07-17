import logging
import re

from pathlib import Path
from pydantic import validate_call
from pyam.utils import escape_regexp

from nomenclature.countries import countries
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import RegionAggregationMapping, RegionProcessor
from nomenclature.processor.region import CommonRegion, NativeRegion

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


class CountryProcessor(RegionProcessor):
    """A RegionProcessor configured for country-level aggregation.

    This is a convenience class that generates region aggregation mappings
    for hierarchies from the region codelist. Defaults to R5/R9/R10 regions.
    """

    @classmethod
    @validate_call(config={"arbitrary_types_allowed": True})
    def from_codelist(
        cls,
        dsd: DataStructureDefinition,
        models: list[str],
        hierarchies: list[str] = ["R5", "R9", "R10"],
        skip_patterns: list[str] | None = ["Other (R*)"],
    ):
        """Create a processor for country-to-regional aggregation.

        This factory method generates region aggregation mappings on-the-fly by
        extracting regions with constituent countries matching the specified
        hierarchies from the region codelist.

        Parameters
        ----------
        dsd : DataStructureDefinition
            Project data structure definition containing region and variable codelists.
        models : list[str]
            Models for which to apply the aggregation.
        hierarchies : list[str]
            List of hierarchy values to match (e.g., ["R5", "R9", "R10"]).
            Regions with these exact hierarchy values will be used for aggregation.
        skip_patterns : list[str], optional
            Optional regex patterns to skip certain regions from aggregation.

        Returns
        -------
        CountryProcessor
            A CountryProcessor instance with generated mappings.

        Raises
        ------
            If regions with the specified hierarchies lack constituent country information.
        """
        models = models or dsd.config.processor.country
        if not models:
            raise ValueError("No models configured for country processor")
        skip_patterns = ["Other (R*)"] + (skip_patterns or [])
        available_hierarchies = set(hierarchies) & set(dsd.region.hierarchy)

        # Extract regional aggregates from codelist for given hierarchies
        regional_aggregates = {}
        for hierarchy in available_hierarchies:
            for code in dsd.region.filter(hierarchy=hierarchy).items():
                if skip_patterns and any(
                    re.match(escape_regexp(pattern), code[0])
                    for pattern in skip_patterns
                ):
                    continue
                if not code[1].countries:
                    raise ValueError(
                        f"List of constituent countries for region '{code[0]}' "
                        "not found in codelist."
                    )
                if code[1].countries:
                    regional_aggregates[code[0]] = code[1].countries

        if not regional_aggregates:
            logger.warning(
                f"No regional aggregates for hierarchies {hierarchies} found in "
                "region codelist."
            )

        # Get all countries from the codelist
        country_names = set(countries.names)
        all_countries_in_codelist = [
            region_name
            for region_name in dsd.region.mapping.keys()
            if region_name in country_names
        ]

        # Create native regions for all countries (to keep them in output)
        native_regions = [
            NativeRegion(name=country) for country in all_countries_in_codelist
        ]

        # Create common regions for aggregation
        common_regions = [
            CommonRegion(name=region_name, constituent_regions=constituent_countries)
            for region_name, constituent_countries in regional_aggregates.items()
        ]

        # Create a mapping for all models
        mapping = RegionAggregationMapping(
            model=models,
            file=Path(__file__),
            native_regions=native_regions,
            common_regions=common_regions,
        )

        return cls(
            mappings={model: mapping for model in models},
            region_codelist=dsd.region,
            variable_codelist=dsd.variable,
        )
