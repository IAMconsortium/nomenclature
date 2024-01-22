import abc

from pyam import IamDataFrame
from pydantic import BaseModel


class Processor(BaseModel, abc.ABC):
    @abc.abstractmethod
    def apply(self, df: IamDataFrame) -> IamDataFrame:
        raise NotImplementedError
