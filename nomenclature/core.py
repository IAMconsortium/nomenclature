import logging

import pyam
from pydantic import validate_call

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import Processor, RegionProcessor

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

    * Validation against the codelists of a DataStructureDefinition
    * Region-processing, which can consist of three parts:
        1. Model native regions not listed in the model mapping will be dropped
        2. Model native regions can be renamed
        3. Aggregation from model native regions to "common regions"
    * Validation of consistency across the variable hierarchy

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        Scenario data to be validated and aggregated.
    dsd : :class:`DataStructureDefinition`
        Codelists that are used for validation.
    dimensions : list, optional
        Dimensions to be used in the validation, defaults to all dimensions defined in
        `dsd`
    processor : :class:`RegionProcessor`, optional
        Region processor to perform region renaming and aggregation (if given)

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

    if (
        any(isinstance(p, RegionProcessor) for p in processor)
        and "region" in dimensions
    ):
        dimensions.remove("region")

    dsd.validate(df, dimensions=dimensions)

    for p in processor:
        df = p.apply(df)

    # check consistency across the variable hierarchy
    error = dsd.check_aggregate(df)
    if error is not None:
        logger.error(f"These variables are not the sum of their components:\n{error}")
        raise ValueError("The validation failed. Please check the log for details.")

    return df
