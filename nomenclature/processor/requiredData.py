from pathlib import Path
from typing import List, Optional, Union

import yaml
from pydantic import BaseModel


class RequiredData(BaseModel):

    variable: Union[str, List[str]]
    region: Optional[Union[str, List[str]]]
    years: Optional[Union[int, List[int]]]
    optional: bool = False


class RequiredDataConfig(BaseModel):

    name: str
    required_timeseries: List[RequiredData]

    @classmethod
    def from_file(cls, file: Union[Path, str]) -> "RequiredDataConfig":

        with open(file, "r") as f:
            content = yaml.safe_load(f)
        return cls(**content)
