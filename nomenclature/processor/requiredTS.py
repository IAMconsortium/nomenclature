from typing import List, Union, Optional
from pathlib import Path
from pydantic import BaseModel

import yaml


class RequiredTS(BaseModel):

    variable: Union[str, List[str]]
    region: Optional[Union[str, List[str]]]
    years: Optional[Union[int, List[int]]]
    scenario: Optional[Union[str, List[str]]]
    required: bool = True


class RequiredTSConfig(BaseModel):

    name: str
    required_timeseries: List[RequiredTS]

    @classmethod
    def from_file(cls, file: Union[Path, str]):

        with open(file, "r") as f:
            content = yaml.safe_load(f)
        return cls(**content)
