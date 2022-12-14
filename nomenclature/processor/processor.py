from abc import ABC, abstractmethod

from pyam import IamDataFrame
from pydantic import BaseModel

from nomenclature.definition import DataStructureDefinition


class Processor(BaseModel, ABC):
    @abstractmethod
    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        raise NotImplementedError

    @abstractmethod
    def apply(self, df: IamDataFrame) -> IamDataFrame:
        raise NotImplementedError
