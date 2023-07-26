from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, root_validator, validator

import yaml
from git import Repo


class CodeListConfig(BaseModel):
    dimension: str
    repository: Optional[str]
    repository_dimension_path: Optional[Path]

    @root_validator()
    def set_repository_dimension_path(cls, v):
        if (
            v.get("repository") is not None
            and v.get("repository_dimension_path") is None
        ):
            v["repository_dimension_path"] = f"definitions/{v['dimension']}"
        return v


class RegionCodeListConfig(CodeListConfig):
    country: bool = False


class Repository(BaseModel):
    url: str
    hash: Optional[str]
    release: Optional[str]
    local_path: Optional[Path]  # defined via the `repository` name in the configuration

    @root_validator()
    def check_hash_and_release(cls, v):
        if v.get("hash") and v.get("release"):
            raise ValueError("Either `hash` or `release` can be provided, not both.")
        return v

    @validator("local_path")
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

    region: Optional[RegionCodeListConfig]
    variable: Optional[CodeListConfig]

    @validator("region", "variable", pre=True)
    def add_dimension(cls, v, field):
        return {"dimension": field.name, **v}

    @root_validator
    def check_repository_consistency(cls, values):
        for dimension in ("region", "variable"):
            if (
                values.get("repository")
                and values.get(dimension)
                and values.get(dimension).repository
                and values.get(dimension).repository not in values.get("repository")
            ):
                raise ValueError(
                    (
                        f"Unknown repository '{values.get(dimension).repository}' in"
                        f" {dimension}.repository."
                    )
                )
        return values

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
    definitions: Optional[DataStructureConfig]
    mappings: Optional[RegionMappingConfig]

    @root_validator
    def check_definitions_repository(cls, v):
        definitions_repos = v.get("definitions").repos if v.get("definitions") else {}
        mapping_repos = (
            {"mappings": v.get("mappings").repository} if v.get("mappings") else {}
        )
        repos = {**definitions_repos, **mapping_repos}
        if repos and not v.get("repositories"):
            raise ValueError(
                (
                    "If repositories are used for definitions or mappings, they need "
                    "to be defined under `repositories`"
                )
            )

        for use, repository in repos.items():
            if repository not in v.get("repositories"):
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
