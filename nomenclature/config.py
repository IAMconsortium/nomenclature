from pathlib import Path
from typing import Annotated, Optional

import yaml
from git import Repo
from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
    ConfigDict,
    BeforeValidator,
)


def convert_to_set(v: str | list[str] | set[str]) -> set[str]:
    match v:
        case set(v):
            return v
        case list(v):
            return set(v)
        case str(v):
            return {v}
        case _:
            raise TypeError("`repositories` must be of type str, list or set.")


class CodeListConfig(BaseModel):
    dimension: str
    repositories: Annotated[set[str] | None, BeforeValidator(convert_to_set)] = Field(
        None, alias="repository"
    )
    model_config = ConfigDict(populate_by_name=True)

    @property
    def repository_dimension_path(self) -> str:
        return f"definitions/{self.dimension}"


class RegionCodeListConfig(CodeListConfig):
    country: bool = False


class Repository(BaseModel):
    url: str
    hash: str | None = None
    release: str | None = None
    local_path: Path | None = Field(default=None, validate_default=True)
    # defined via the `repository` name in the configuration

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
    def repos(self) -> dict[str, str]:
        return {
            dimension: getattr(self, dimension).repositories
            for dimension in ("region", "variable")
            if getattr(self, dimension) and getattr(self, dimension).repositories
        }


class RegionMappingConfig(BaseModel):
    repositories: Annotated[set[str], BeforeValidator(convert_to_set)] = Field(
        ..., alias="repository"
    )
    model_config = ConfigDict(populate_by_name=True)


class NomenclatureConfig(BaseModel):
    repositories: dict[str, Repository] = {}
    definitions: Optional[DataStructureConfig] = None
    mappings: Optional[RegionMappingConfig] = None

    @model_validator(mode="after")
    @classmethod
    def check_definitions_repository(
        cls, v: "NomenclatureConfig"
    ) -> "NomenclatureConfig":
        definitions_repos = v.definitions.repos if v.definitions else {}
        mapping_repos = {"mappings": v.mappings.repositories} if v.mappings else {}
        repos = {**definitions_repos, **mapping_repos}
        for use, repositories in repos.items():
            if repositories - v.repositories.keys():
                raise ValueError((f"Unknown repository {repositories} in '{use}'."))
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
