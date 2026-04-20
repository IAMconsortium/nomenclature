import abc
from typing import Annotated

from pyam import IamDataFrame
from pydantic import BaseModel, Field


class Processor(BaseModel, abc.ABC):
    input_data: Annotated[dict[str, list[str]] | None, Field(frozen=True)] = None
    input_meta: Annotated[list[str] | None, Field(frozen=True)] = None
    output_data: Annotated[dict[str, list[str]] | None, Field(frozen=True)] = None
    output_meta: Annotated[list[str] | None, Field(frozen=True)] = None

    @abc.abstractmethod
    def apply(self, df: IamDataFrame) -> IamDataFrame:
        raise NotImplementedError
