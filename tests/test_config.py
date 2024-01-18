from pathlib import Path
from pytest import raises

from nomenclature.config import Repository, NomenclatureConfig

from conftest import TEST_DATA_DIR


def test_hash_and_release_raises():
    with raises(ValueError, match="`hash` or `release` can be provided, not both"):
        NomenclatureConfig.from_file(
            TEST_DATA_DIR / "nomenclature_configs" / "hash_and_release.yaml"
        )


def test_setting_local_path_raises():
    with raises(ValueError, match="`local_path` must not be set"):
        Repository(local_path=Path("."))


def test_unknown_repo_raises():
    with raises(ValueError, match="Unknown repository 'common-definitions'"):
        NomenclatureConfig.from_file(
            TEST_DATA_DIR / "nomenclature_configs" / "unknown_repo.yaml"
        )
