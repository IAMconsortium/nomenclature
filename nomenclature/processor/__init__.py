import abc

from pyam import IamDataFrame
from pydantic import BaseModel


class Processor(BaseModel, abc.ABC):
    @abc.abstractmethod
    def apply(self, df: IamDataFrame) -> IamDataFrame:
        return


from nomenclature.processor.region import (  # noqa
    RegionAggregationMapping,
    RegionProcessor,
)
from nomenclature.processor.required_data import RequiredDataValidator  # noqa
