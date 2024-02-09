from pathlib import Path
from pytest import raises

from nomenclature.config import Repository, NomenclatureConfig, CodeListConfig

from conftest import TEST_DATA_DIR, clean_up_external_repos


def test_hash_and_release_raises():
    with raises(ValueError, match="`hash` or `release` can be provided, not both"):
        NomenclatureConfig.from_file(
            TEST_DATA_DIR / "nomenclature_configs" / "hash_and_release.yaml"
        )


def test_setting_local_path_raises():
    with raises(ValueError, match="`local_path` must not be set"):
        Repository(local_path=Path("."))


def test_unknown_repo_raises():
    with raises(
        ValueError, match="Unknown repository {'common-definitions'} in 'region'"
    ):
        NomenclatureConfig.from_file(
            TEST_DATA_DIR / "nomenclature_configs" / "unknown_repo.yaml"
        )


def test_multiple_definition_repos():
    nomenclature_config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "nomenclature_configs" / "multiple_repos_per_dimension.yaml"
    )
    try:
        exp_repos = {"common-definitions", "legacy-definitions"}
        assert nomenclature_config.repositories.keys() == exp_repos
        assert nomenclature_config.definitions.variable.repositories == exp_repos
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


def test_codelist_config_set_input():
    exp_repos = {"repo1", "repo2"}
    code_list_config = CodeListConfig(dimension="variable", repositories=exp_repos)
    assert code_list_config.repositories == exp_repos


def test_multiple_mapping_repos():
    nomenclature_config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "nomenclature_configs" / "multiple_repos_for_mapping.yaml"
    )
    try:
        exp_repos = {"common-definitions", "legacy-definitions"}
        assert nomenclature_config.mappings.repositories == exp_repos
        assert nomenclature_config.repositories.keys() == exp_repos
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


def test_double_stacked_external_repo_raises(monkeypatch):
    repo = Repository(url="lorem ipsum")
    monkeypatch.setitem(
        repo.__dict__,
        "local_path",
        TEST_DATA_DIR / "double_stacked_external_repo",
    )
    match = "No external repos allowed in external repo"
    with raises(ValueError, match=match):
        repo.check_external_repo_double_stacking()
