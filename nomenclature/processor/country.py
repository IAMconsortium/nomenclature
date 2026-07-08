import logging
from pathlib import Path

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.region import RegionProcessor

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


def create_country_processor(
    dsd: DataStructureDefinition,
    models: list[str] | None = None,
) -> RegionProcessor:
    """Create a RegionProcessor configured for country-level aggregation.

    This is a convenience function that generates region aggregation mappings
    for R5/R9/R10 hierarchies from the region codelist.

    Parameters
    ----------
    dsd : DataStructureDefinition
        Project data structure definition.
    models : list[str], optional
        Models for which to apply country aggregation. Defaults to the list configured
        under ``config.processor.country`` in *dsd*.

    Returns
    -------
    RegionProcessor
        A RegionProcessor configured for country aggregation.
    """
    models = models or dsd.config.processor.country

    if not models:
        raise ValueError("No models configured for country processor")

    available_hierarchies = [
        hierarchy
        for hierarchy in ["R5", "R9", "R10"]
        if dsd.region.by_hierarchy(hierarchy)
    ]

    return RegionProcessor.from_country_codelist(
        dsd=dsd,
        hierarchies=available_hierarchies,
        models=models,
        skip_patterns=["Other (R*)"],
    )
