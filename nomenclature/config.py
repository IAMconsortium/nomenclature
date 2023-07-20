from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, root_validator

import yaml
from git import Repo


class CodeListConfig(BaseModel):
    repository: Optional[str]
    hash: Optional[str]
    release: Optional[str]

    @root_validator()
    def check_hash_and_release(cls, v):
        if v.get("hash") and v.get("release"):
            raise ValueError("Either 'hash' or 'release' can be provided, not both.")
        return v

    @property
    def revision(self):
        return self.hash or self.release or "main"

    @property
    def repository_name(self):
        return self.repository.split("/")[-1].split(".")[0]

    def fetch_repo(self, to_path="./common-definitions"):
        to_path = to_path if isinstance(to_path, Path) else Path(to_path)

        if not to_path.is_dir():
            repo = Repo.clone_from(self.repository, to_path)
        else:
            repo = Repo(to_path)
            repo.remotes.origin.fetch()
        repo.git.reset("--hard")
        repo.git.checkout(self.revision)
        repo.git.reset("--hard")
        repo.git.clean("-xdf")
        if self.revision == "main":
            repo.remotes.origin.pull()


class RegionCodeListConfig(CodeListConfig):
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

        return cls(region=RegionCodeListConfig(**config["region"]))
