from pathlib import Path
from typing import List, Optional, Union

import yaml
from pydantic import BaseModel


class RequiredTS(BaseModel):

    variable: Union[str, List[str]]
    region: Optional[Union[str, List[str]]]
    years: Optional[Union[int, List[int]]]
    optional: bool = False


class RequiredTSConfig(BaseModel):

    name: str
    required_timeseries: List[RequiredTS]

    @classmethod
    def from_file(cls, file: Union[Path, str]) -> "RequiredTSConfig":

        with open(file, "r") as f:
            content = yaml.safe_load(f)
        return cls(**content)
