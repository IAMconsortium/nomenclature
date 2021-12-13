import copy
from pyam import IamDataFrame
from pydantic import validate_arguments

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.region import RegionProcessor


@validate_arguments(config=dict(arbitrary_types_allowed=True))
def process(
    df: IamDataFrame,
    dsd: DataStructureDefinition,
    dimensions: list = None,
    processor: RegionProcessor = None,
):
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
