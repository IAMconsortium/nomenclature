from enum import Enum
from pathlib import Path
from typing import Any
import re

import yaml
from git import Repo
from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
    ConfigDict,
)
from nomenclature.code import Code
from pyam.str import escape_regexp


class CodeListFromRepository(BaseModel):
    name: str
    include: list[dict[str, Any]] = [{"name": "*"}]
    exclude: list[dict[str, Any]] = Field(default_factory=list)

    def filter_function(self, code: Code, filter: dict[str, Any], keep: bool):
        # if is list -> recursive
        # if is str -> escape all special characters except "*" and use a regex
        # if is int -> match exactly
        # if is None -> Attribute does not exist therefore does not match
        def check_attribute_match(code_value, filter_value):
            if isinstance(filter_value, int):
                return code_value == filter_value
            if isinstance(filter_value, str):
                pattern = re.compile(escape_regexp(filter_value) + "$")
                return re.match(pattern, code_value) is not None
            if isinstance(filter_value, list):
                return any(
                    check_attribute_match(code_value, value) for value in filter_value
                )
            if filter_value is None:
                return False
            raise ValueError("Something went wrong with the filtering")

        filter_match = all(
            check_attribute_match(getattr(code, attribute, None), value)
            for attribute, value in filter.items()
        )
        if keep:
            return filter_match
        else:
            return not filter_match

    def filter_list_of_codes(self, list_of_codes: list[Code]) -> list[Code]:
        # include first
        filter_result = [
            code
            for code in list_of_codes
            if any(
                self.filter_function(
                    code,
                    filter,
                    keep=True,
                )
                for filter in self.include
            )
        ]

        if self.exclude:
            filter_result = [
                code
                for code in filter_result
                if any(
                    self.filter_function(code, filter, keep=False)
                    for filter in self.exclude
                )
            ]

        return filter_result


class CodeListConfig(BaseModel):
    dimension: str | None = None
    repositories: list[CodeListFromRepository] = Field(
        default_factory=list, alias="repository"
    )
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("repositories", mode="before")
    @classmethod
    def add_name_if_necessary(cls, v: list):
        return [
            {"name": repository} if isinstance(repository, str) else repository
            for repository in v
        ]

    @field_validator("repositories", mode="before")
    @classmethod
    def convert_to_list_of_repos(cls, v):
        if not isinstance(v, list):
            return [v]
        return v

    @property
    def repository_dimension_path(self) -> str:
        return f"definitions/{self.dimension}"


class RegionCodeListConfig(CodeListConfig):
    country: bool = False
    nuts: dict[str, str | list[str]] | None = None

    @field_validator("nuts")
    @classmethod
    def check_nuts(
        cls, v: dict[str, str | list[str]] | None
    ) -> dict[str, str | list[str]] | None:
        if v and not all(k in ["nuts-1", "nuts-2", "nuts-3"] for k in v.keys()):
            raise ValueError(
                "Invalid fields for `nuts` in configuration. "
                "Allowed values are: 'nuts-1', 'nuts-2' and 'nuts-3'."
            )
        return v


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
        self.check_external_repo_double_stacking()

    def check_external_repo_double_stacking(self):
        nomenclature_config = self.local_path / "nomenclature.yaml"
        if nomenclature_config.is_file():
            with open(nomenclature_config, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if config.get("repositories"):
                raise ValueError(
                    (
                        "External repos cannot again refer to external repos, "
                        f"found in nomenclature.yaml in '{self.url}'"
                    )
                )


class DataStructureConfig(BaseModel):
    """A class for configuration of a DataStructureDefinition

    Attributes
    ----------
    region : RegionCodeListConfig
        Attributes for configuring the RegionCodeList

    """

    model: CodeListConfig = Field(default_factory=CodeListConfig)
    scenario: CodeListConfig = Field(default_factory=CodeListConfig)
    region: RegionCodeListConfig = Field(default_factory=RegionCodeListConfig)
    variable: CodeListConfig = Field(default_factory=CodeListConfig)

    @field_validator("model", "scenario", "region", "variable", mode="before")
    @classmethod
    def add_dimension(cls, v, info: ValidationInfo):
        return {"dimension": info.field_name, **v}

    @property
    def repos(self) -> dict[str, str]:
        return {
            dimension: getattr(self, dimension).repositories
            for dimension in ("model", "scenario", "region", "variable")
            if getattr(self, dimension).repositories
        }


class MappingRepository(BaseModel):
    name: str


class RegionMappingConfig(BaseModel):
    repositories: list[MappingRepository] = Field(
        default_factory=list, alias="repository"
    )
    model_config = ConfigDict(populate_by_name=True)

    @field_validator("repositories", mode="before")
    @classmethod
    def add_name_if_necessary(cls, v: list):
        return [
            {"name": repository} if isinstance(repository, str) else repository
            for repository in v
        ]

    @field_validator("repositories", mode="before")
    def convert_to_set_of_repos(cls, v):
        if not isinstance(v, list):
            return [v]
        return v


class DimensionEnum(str, Enum):
    model = "model"
    scenario = "scenario"
    variable = "variable"
    region = "region"
    subannual = "subannual"


class NomenclatureConfig(BaseModel):
    dimensions: None | list[DimensionEnum] = None
    repositories: dict[str, Repository] = Field(default_factory=dict)
    definitions: DataStructureConfig = Field(default_factory=DataStructureConfig)
    mappings: RegionMappingConfig = Field(default_factory=RegionMappingConfig)

    model_config = ConfigDict(use_enum_values=True)

    @model_validator(mode="after")
    @classmethod
    def check_definitions_repository(
        cls, v: "NomenclatureConfig"
    ) -> "NomenclatureConfig":
        mapping_repos = {"mappings": v.mappings.repositories} if v.mappings else {}
        repos = {**v.definitions.repos, **mapping_repos}
        for use, repositories in repos.items():
            repository_names = [repository.name for repository in repositories]
            if unknown_repos := repository_names - v.repositories.keys():
                raise ValueError((f"Unknown repository {unknown_repos} in '{use}'."))
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
