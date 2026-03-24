import logging
import gc
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from shutil import rmtree

import yaml
from git import Repo
from pyam import IamDataFrame
from pyam.str import escape_regexp
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from nomenclature.exceptions import TimeDomainError, TimeDomainErrorGroup
from nomenclature.utils import handle_remove_readonly

logger = logging.getLogger(__name__)


class CodeListFromRepository(BaseModel):
    name: str
    include: list[dict[str, Any]] = [{"name": "*"}]
    exclude: list[dict[str, Any]] = Field(default_factory=list)


class CodeListConfig(BaseModel):
    dimension: str | None = None
    repositories: list[CodeListFromRepository] = Field(
        default_factory=list, alias="repository"
    )
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    @model_validator(mode="before")
    @classmethod
    def check_no_filter_at_dimension_level(cls, v):
        if isinstance(v, dict):
            for field in ("include", "exclude"):
                if field in v:
                    raise ValueError(
                        f"'{field}' must be nested inside 'repository', not at the "
                        f"dimension level."
                    )
        return v

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
    nuts: dict[str, str | list[str] | bool] | None = None

    @field_validator("nuts")
    @classmethod
    def check_nuts(
        cls, v: dict[str, str | list[str] | bool] | None
    ) -> dict[str, str | list[str] | bool] | None:
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

    @property
    def has_auto_update(self) -> bool:
        return self.hash is None and self.release is None

    def fetch_repo(self, to_path):
        to_path = to_path if isinstance(to_path, Path) else Path(to_path)

        if not to_path.is_dir():
            repo = Repo.clone_from(self.url, to_path)
        else:
            repo = Repo(to_path)
            # If the URL has changed, remove existing directory and re-clone
            if repo.remotes.origin.url != self.url:
                logger.warning(
                    f"Repository URL changed from '{repo.remotes.origin.url}' to '{self.url}'. "
                    f"Re-cloning repository to '{to_path}'..."
                )
                repo.close()  # Close repo before removing directory
                del repo  # Delete reference to allow garbage collection
                gc.collect()  # Force garbage collection to release file handles

                rmtree(to_path, onerror=handle_remove_readonly)
                repo = Repo.clone_from(self.url, to_path)
            else:
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
    def repos(self) -> dict[str, list[CodeListFromRepository]]:
        return {
            dimension: getattr(self, dimension).repositories
            for dimension in ("model", "scenario", "region", "variable")
            if getattr(self, dimension).repositories
        }


class MappingRepository(BaseModel):
    name: str
    include: list[str] = ["*"]

    @property
    def regex_include_patterns(self):
        return [re.compile(escape_regexp(pattern) + "$") for pattern in self.include]

    def match_models(self, models: list[str]) -> list[str]:
        return [
            model
            for model in models
            for pattern in self.regex_include_patterns
            if re.match(pattern, model) is not None
        ]

    def validate_include_patterns(self, models: list[str]) -> None:
        """Raise if any include pattern matches no models in the external repo."""
        if errors := [
            ValueError(f"No models found for include pattern: '{pattern}'")
            for pattern, regex in zip(self.include, self.regex_include_patterns)
            if not any(re.match(regex, model) for model in models)
        ]:
            raise ExceptionGroup("Mapping include pattern validation failed", errors)


class RegionMappingConfig(BaseModel):
    repositories: list[MappingRepository] = Field(
        default_factory=list, alias="repository"
    )
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    @field_validator("repositories", mode="before")
    @classmethod
    def add_name_if_necessary(cls, v: list):
        return [
            {"name": repository} if isinstance(repository, str) else repository
            for repository in v
        ]

    @field_validator("repositories", mode="before")
    @classmethod
    def convert_to_set_of_repos(cls, v):
        if not isinstance(v, list):
            return [v]
        return v


class TimeDomainConfig(BaseModel):
    year_allowed: bool = Field(default=True, alias="year")
    datetime_allowed: bool = Field(default=False, alias="datetime")
    timezone: str | None = Field(
        default=None,
        pattern=r"^UTC([+-])(1[0-4]|0?[0-9]):([0-5][0-9])$",
        # pattern_msg="Invalid timezone format. Expected format: 'UTC±HH:MM'."
    )

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    @model_validator(mode="after")
    @classmethod
    def validate_datetime_and_timezone(
        cls, v: "TimeDomainConfig"
    ) -> "TimeDomainConfig":
        if v.timezone is not None and not v.datetime_allowed:
            raise ValueError("'timezone' is set but 'datetime' is not allowed")
        return v

    @property
    def mixed_allowed(self) -> bool:
        return self.year_allowed and self.datetime_allowed

    @property
    def datetime_format(self) -> str:
        # if year is a separate column, exclude it from format
        # if not, datetime is coerced in IamDataFrame, and include seconds
        return "%Y-%m-%d %H:%M:%S" if self.datetime_allowed else None

    def check_datetime_format(self, df: IamDataFrame) -> None:
        """Validate that datetime values conform to configured format and timezone."""
        errors = []
        _datetime = [d for d in df.time if isinstance(d, datetime)]
        for d in _datetime:
            try:
                _dt = datetime.strptime(str(d), self.datetime_format + "%z")
                # only check timezone if a specific timezone is required
                if self.timezone and not _dt.tzname() == self.timezone:
                    errors.append(TimeDomainError(f"{d} - invalid timezone"))
            except ValueError:
                errors.append(TimeDomainError(f"{d} - missing timezone"))
        if errors:
            raise TimeDomainErrorGroup(
                "The following datetime values are invalid:", errors
            )

    def validate_datetime(self, df: IamDataFrame) -> None:
        """Validate datetime coordinates against allowed format and/or timezone."""
        if df.time_domain == "year":
            if not self.year_allowed:
                raise TimeDomainError(
                    "Invalid time domain - `year` found, but not allowed."
                )

        elif df.time_domain == "mixed":
            if not self.mixed_allowed:
                raise TimeDomainError(
                    "Invalid time domain - `mixed` found, but not allowed."
                )

            self.check_datetime_format(df)
        elif df.time_domain == "datetime":
            if not self.datetime_allowed:
                raise TimeDomainError(
                    "Invalid time domain - `datetime` found, but not allowed."
                )
            self.check_datetime_format(df)
        else:
            raise TimeDomainError(
                "IamDataFrame.time_domain must be one of ['year', 'mixed', "
                f"datetime'], found '{df.time_domain}'"
            )


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
    illegal_characters: list[str] = Field(
        default=[":", ";", '"'], alias="illegal-characters"
    )
    time_domain: TimeDomainConfig = Field(
        default_factory=TimeDomainConfig, alias="time-domain"
    )

    model_config = ConfigDict(
        use_enum_values=True, validate_by_name=True, validate_by_alias=True
    )

    @field_validator("illegal_characters", mode="before")
    @classmethod
    def check_illegal_chars(cls, v: str | list[str]) -> list[str]:
        return v if isinstance(v, list) else [v]

    @model_validator(mode="after")
    @classmethod
    def check_definitions_repository(
        cls, v: "NomenclatureConfig"
    ) -> "NomenclatureConfig":
        mapping_repos = {"mappings": v.mappings.repositories} if v.mappings else {}
        repos: dict[str, list[MappingRepository]] = {
            **v.definitions.repos,
            **mapping_repos,
        }
        for use, repositories in repos.items():
            repository_names = [repository.name for repository in repositories]
            if unknown_repos := repository_names - v.repositories.keys():
                raise ValueError((f"Unknown repository {unknown_repos} in '{use}'."))
        return v

    def fetch_repos(self, target_folder: Path):
        for repo_name, repo in self.repositories.items():
            repo.fetch_repo(target_folder / repo_name)

    def validate_mapping_includes(self) -> None:
        """Validate that all mapping include patterns match at least one model."""
        for repository in self.mappings.repositories:
            repo_mapping_dir = (
                self.repositories[repository.name].local_path / "mappings"
            )
            all_models: list[str] = []
            errors = []
            for file in repo_mapping_dir.glob("**/*.y*ml"):
                try:
                    content = file.read_text(encoding="utf-8")
                    data = yaml.safe_load(content)
                    if not isinstance(data, dict):
                        raise TypeError(
                            f"Expected a mapping at the top level, got {type(data).__name__}"
                        )
                    model_value = data.get("model")
                    if not model_value:
                        raise KeyError("No 'model' specified in mapping file")
                    models_in_file = (
                        model_value if isinstance(model_value, list) else [model_value]
                    )
                    all_models.extend(models_in_file)
                except Exception as e:
                    errors.append(Exception(f"{file}: {type(e).__name__}: {e}"))

            if errors:
                raise ExceptionGroup(
                    f"Failed to parse mapping files in repository '{repository.name}' at '{repo_mapping_dir}'",
                    errors,
                )
            if all_models:
                repository.validate_include_patterns(all_models)
            else:
                logger.warning(
                    f"No valid model mappings found in repository '{repository.name}' at '{repo_mapping_dir}'."
                )

    @classmethod
    def from_file(cls, file: Path, dry_run: bool = False):
        """Read a NomenclatureConfig from a file

        Parameters
        ----------
        file : :class:`pathlib.Path` or path-like
            Path to config file

        """
        with open(file, "r", encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
        instance = cls(**config)
        if not dry_run:
            instance.fetch_repos(file.parent)
            instance.validate_mapping_includes()
        return instance
