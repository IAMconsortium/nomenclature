from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel

import yaml


class RegionCodeListConfig(BaseModel):
    country: Optional[bool]


class DataStructureConfig(BaseModel):
    """A class for configuration of a DataStructureDefinition

    Attributes
    ----------
    region : RegionCodeListConfig
        Attributes for configuring the RegionCodeList

    """

    region: Optional[RegionCodeListConfig]

    @classmethod
    def from_file(cls, path: Path, file: str):
        """Read a DataStructureConfig from a file

        Parameters
        ----------
        path : :class:`pathlib.Path` or path-like
            `definitions` directory
        file : str
            File name

        """
        with open(path / file, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream)

        return cls(
            region=RegionCodeListConfig(**config["region"])
        )
