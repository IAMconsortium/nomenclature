import logging

import pyam
from pydantic import validate_call

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import Processor, RegionProcessor
from nomenclature.processor.nuts import NutsProcessor

logger = logging.getLogger(__name__)


@validate_call(config={"arbitrary_types_allowed": True})
def process(
    df: pyam.IamDataFrame,
    dsd: DataStructureDefinition,
    dimensions: list[str] | None = None,
    processor: Processor | list[Processor] | None = None,
) -> pyam.IamDataFrame:
    """Function for validation and region aggregation in one step

    This function is the recommended way of using the nomenclature package. It performs
    the following operations:

    * Validation against the codelists and criteria of a :class:`DataStructureDefinition`
    * Region processing, which can occur via one or more :class:`Processor` instances. This can be:
        * Region aggregation (via :class:`RegionProcessor`), which renames and aggregates based on user-provided mappings.
            1. Model native regions not listed in the model mapping will be dropped
            2. Model native regions can be renamed
            3. Aggregation from model native regions to "common regions"
        * NUTS aggregation (via :class:`NutsProcessor`), which aggregates NUTS3 -> NUTS2 -> NUTS1 -> Country -> EU27(+UK)
    * Validation of consistency across the variable hierarchy

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        Scenario data to be validated and aggregated.
    dsd : :class:`DataStructureDefinition`
        Codelists that are used for validation.
    dimensions : list, optional
        Dimensions to be used in the validation, defaults to all dimensions defined in
        ``dsd``.
    processor : :class:`Processor` or list of :class:`Processor`, optional
        One or more processors to apply. Runs before any config-declared processors.

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Processed scenario data

    Raises
    ------
    ValueError
        If the :class:`pyam.IamDataFrame` fails the validation.
    """

    processor = processor or []
    processor = processor if isinstance(processor, list) else [processor]

    dimensions = dimensions or dsd.dimensions

    # Auto-instantiate processors declared in nomenclature.yaml under 'processors'
    # Explicit processors take precedence; config-based ones are appended after.
    if dsd.config.processor.region_processor and not any(
        isinstance(p, RegionProcessor) for p in processor
    ):
        processor = processor + [
            RegionProcessor.from_directory(dsd.project_folder / "mappings", dsd)
        ]

    if dsd.config.processor.nuts is not None and not any(
        isinstance(p, NutsProcessor) for p in processor
    ):
        processor = processor + [NutsProcessor.from_definition(dsd)]

    if (
        any(isinstance(p, (RegionProcessor, NutsProcessor)) for p in processor)
        and "region" in dimensions
    ):
        dimensions.remove("region")

    # validate against the codelists
    dsd.validate(df, dimensions=dimensions)

    # run the processors
    for p in processor:
        df = p.apply(df)

    # check consistency across the variable hierarchy
    error = dsd.check_aggregate(df)
    if not error.empty:
        raise ValueError(
            f"These variables are not the sum of their components:\n{error}"
        )

    return df
