import pytest
from nomenclature.testing import assert_valid_yaml
from conftest import TEST_DATA_DIR


def test_assert_yaml():
    """Check that importing a full-fledged (correct) nomenclature definition passes"""
    assert_valid_yaml(TEST_DATA_DIR / "validation_nc")


def test_assert_yaml_fails():
    """Check that parsing an invalid yaml raises expected error"""
    match = "Parsing the yaml files failed. Please check the log for details."
    with pytest.raises(AssertionError, match=match):
        assert_valid_yaml(TEST_DATA_DIR / "invalid_yaml")
