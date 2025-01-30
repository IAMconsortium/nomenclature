from pathlib import Path
import pytest
from pytest import raises

from nomenclature.config import Repository, NomenclatureConfig, MappingRepository

from conftest import TEST_DATA_DIR, clean_up_external_repos

MODULE_TEST_DATA_DIR = TEST_DATA_DIR / "config"


def test_hash_and_release_raises():
    with raises(ValueError, match="`hash` or `release` can be provided, not both"):
        NomenclatureConfig.from_file(MODULE_TEST_DATA_DIR / "hash_and_release.yaml")


def test_setting_local_path_raises():
    with raises(ValueError, match="`local_path` must not be set"):
        Repository(local_path=Path("."))


def test_unknown_repo_raises():
    with raises(
        ValueError, match="Unknown repository {'common-definitions'} in 'region'"
    ):
        NomenclatureConfig.from_file(MODULE_TEST_DATA_DIR / "unknown_repo.yaml")


def test_multiple_definition_repos():
    nomenclature_config = NomenclatureConfig.from_file(
        MODULE_TEST_DATA_DIR / "multiple_repos_per_dimension.yaml"
    )
    try:
        exp_repos = {"common-definitions", "legacy-definitions"}
        assert nomenclature_config.repositories.keys() == exp_repos
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


def test_multiple_mapping_repos():
    nomenclature_config = NomenclatureConfig.from_file(
        MODULE_TEST_DATA_DIR / "multiple_repos_for_mapping.yaml"
    )
    try:
        exp_repos = {"common-definitions", "legacy-definitions"}
        assert nomenclature_config.repositories.keys() == exp_repos
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


def test_double_stacked_external_repo_raises(monkeypatch):
    repo = Repository(url="lorem ipsum")
    monkeypatch.setitem(
        repo.__dict__,
        "local_path",
        MODULE_TEST_DATA_DIR / "double_stacked_external_repo",
    )
    match = "External repos cannot again refer to external repos"
    with raises(ValueError, match=match):
        repo.check_external_repo_double_stacking()


def test_config_dimensions():
    config = NomenclatureConfig.from_file(MODULE_TEST_DATA_DIR / "dimensions.yaml")
    assert set(config.dimensions) == {
        "scenario",
        "region",
        "variable",
    }


def test_invalid_config_dimensions_raises():
    with raises(
        ValueError,
        match=(
            "Input should be 'model', 'scenario', 'variable',"
            " 'region' or 'subannual'"
        ),
    ):
        NomenclatureConfig(dimensions=["year"])


@pytest.mark.parametrize(
    "config_file",
    ["external_repo_filters.yaml", "multiple_external_repos_filters.yaml"],
)
def test_config_with_filter(config_file):
    config = NomenclatureConfig.from_file(TEST_DATA_DIR / "config" / config_file)
    try:
        assert isinstance(config.definitions.variable.repositories, list)
    finally:
        clean_up_external_repos(config.repositories)


def test_config_external_repo_mapping_filter():
    config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "config" / "filter_mappings.yaml"
    )
    exp = MappingRepository(
        name="common-definitions", include=["MESSAGEix-GLOBIOM 2.1-M-R12"]
    )
    try:
        assert isinstance(config.mappings.repositories, list)
        assert config.mappings.repositories[0] == exp
    finally:
        clean_up_external_repos(config.repositories)
