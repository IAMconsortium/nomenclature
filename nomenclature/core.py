import copy
from typing import List, Optional

import pyam
from pydantic import validate_arguments

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.region import RegionProcessor


@validate_arguments(config=dict(arbitrary_types_allowed=True))
def process(
    df: pyam.IamDataFrame,
    dsd: DataStructureDefinition,
    dimensions: Optional[List[str]] = None,
    processor: Optional[RegionProcessor] = None,
) -> pyam.IamDataFrame:
    """Function for validation and region aggregation in one step

    This function is the recommended way of using the nomenclature package. It performs
    two operations:

    * Validation against the codelists of a DataStructureDefinition
    * Region-processing, which can consist of three parts:
        1. Model native regions not mentioned in the model mapping will be dropped
        2. Model native regions can be renamed
        3. Aggregation from model native regions to "common regions"

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
    """
    # The deep copy is needed so we don't alter dsd in dimensions.remove("region")
    dimensions = copy.deepcopy(dimensions or dsd.dimensions)
    if processor is None:
        return dsd.validate(df, dimensions=dimensions)

    if "region" in dimensions:
        dimensions.remove("region")
        dsd.validate(df, dimensions=dimensions)
        df = processor.apply(df, dsd)
        dsd.validate(df, dimensions=["region"])
    else:
        dsd.validate(df, dimensions=dimensions)
        df = processor.apply(df, dsd)
    return df
