from pathlib import Path
from typing import Dict
from pydantic import BaseModel, validator

import yaml


class DataStructureConfig(BaseModel):
    """A class for configuration of a DataStructureDefinition

    Attributes
    ----------
    config : dict
        Attributes for configuring the DataStructureDefinition

    """

    config: Dict[str, Dict] = {}

    def get(self, key):
        return self.config.get(key)

    @classmethod
    def from_file(cls, path: Path, file: str, dimensions: list):
        """Read a DataStructureConfig from a file

        Parameters
        ----------
        path : :class:`pathlib.Path` or path-like
            `definitions` directory
        file : str
            File name
        dimensions : list
            List of valid dimensions

        """
        with open(path / file, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream)

            if invalid_config := [i for i in config if i not in dimensions]:
                raise ValueError(f"Invalid entries in configuration: {invalid_config}")

        return cls(config=config)
