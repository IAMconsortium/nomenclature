from pathlib import Path
from typing import Dict, Optional

import yaml
from git import Repo
from pydantic import BaseModel, ValidationInfo, field_validator, model_validator


class CodeListConfig(BaseModel):
    dimension: str
    repository: str | None = None
    repository_dimension_path: Path | None = None

    @model_validator(mode="after")
    @classmethod
    def set_repository_dimension_path(cls, v: "CodeListConfig") -> "CodeListConfig":
        if v.repository is not None and v.repository_dimension_path is None:
            v.repository_dimension_path = f"definitions/{v.dimension}"
        return v


class RegionCodeListConfig(CodeListConfig):
    country: bool = False


class Repository(BaseModel):
    url: str
    hash: str | None = None
    release: str | None = None
    local_path: Path | None = (
        None  # defined via the `repository` name in the configuration
    )

    @model_validator(mode="after")
    @classmethod
    def check_hash_and_release(cls, v: "Repository") -> "Repository":
        if v.hash and v.release:
            raise ValueError("Either `hash` or `release` can be provided, not both.")
        return v

    @field_validator("local_path")
    @classmethod
    def check_path_empty(cls, v):
        if v is not None:
            raise ValueError("The `local_path` must not be set as part of the config.")
        return v

    @property
    def revision(self):
        return self.hash or self.release or "main"

    def fetch_repo(self, to_path):
        to_path = to_path if isinstance(to_path, Path) else Path(to_path)

        if not to_path.is_dir():
            repo = Repo.clone_from(self.url, to_path)
        else:
            repo = Repo(to_path)
            repo.remotes.origin.fetch()
        self.local_path = to_path
        repo.git.reset("--hard")
        repo.git.checkout(self.revision)
        repo.git.reset("--hard")
        repo.git.clean("-xdf")
        if self.revision == "main":
            repo.remotes.origin.pull()


class DataStructureConfig(BaseModel):
    """A class for configuration of a DataStructureDefinition

    Attributes
    ----------
    region : RegionCodeListConfig
        Attributes for configuring the RegionCodeList

    """

    region: Optional[RegionCodeListConfig] = None
    variable: Optional[CodeListConfig] = None

    @field_validator("region", "variable", mode="before")
    @classmethod
    def add_dimension(cls, v, info: ValidationInfo):
        return {"dimension": info.field_name, **v}

    @property
    def repos(self) -> Dict[str, str]:
        return {
            dimension: getattr(self, dimension).repository
            for dimension in ("region", "variable")
            if getattr(self, dimension) and getattr(self, dimension).repository
        }


class RegionMappingConfig(BaseModel):
    repository: str


class NomenclatureConfig(BaseModel):
    repositories: Dict[str, Repository] = {}
    definitions: Optional[DataStructureConfig] = None
    mappings: Optional[RegionMappingConfig] = None

    @model_validator(mode="after")
    @classmethod
    def check_definitions_repository(
        cls, v: "NomenclatureConfig"
    ) -> "NomenclatureConfig":
        definitions_repos = v.definitions.repos if v.definitions else {}
        mapping_repos = {"mappings": v.mappings.repository} if v.mappings else {}
        repos = {**definitions_repos, **mapping_repos}
        if repos and not v.repositories:
            raise ValueError(
                (
                    "If repositories are used for definitions or mappings, they need "
                    "to be defined under `repositories`"
                )
            )

        for use, repository in repos.items():
            if repository not in v.repositories:
                raise ValueError((f"Unknown repository '{repository}' in {use}."))
        return v

    def fetch_repos(self, target_folder: Path):
        for repo_name, repo in self.repositories.items():
            repo.fetch_repo(target_folder / repo_name)

    @classmethod
    def from_file(cls, file: Path):
        """Read a DataStructureConfig from a file

        Parameters
        ----------
        file : :class:`pathlib.Path` or path-like
            Path to config file

        """
        with open(file, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
        instance = cls(**config)
        instance.fetch_repos(file.parent)
        return instance
