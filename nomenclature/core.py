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

   This function is the recommended way of using the nomenclature package
   for validation and region-processing.

    Parameters
    ----------
    df : pyam.IamDataFrame
        Input data to be validated and aggregated.
    dsd : DataStructureDefinition
        Data templates that are used for validation.
    dimensions : list, optional
        Dimensions to be used in the validation, defaults to all dimensions defined in *dsd* 
    processor : Optional[RegionProcessor], optional
        Region processor that will perform region renaming and aggregation if provided

    Returns
    -------
    pyam.IamDataFrame
        Processed data frame

    Notes
    -----
    The above mentioned "subtleties" in the order of operations is related to the fact
    that as part of the region processing, three things can occur:

    1. Model native regions not mentioned in the model mapping will be dropped
    2. Model native regions can be renamed
    3. Common regions based on aggregated model native regions weill be newly created.

    As each of these three can affects the outcome of the region validation, this
    validation step needs to be performed *after* aggregation.
    Since none of the other dimensions (e.g. variables, scenarios, etc...) are affected
    by aggregation they can be validated before.
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
