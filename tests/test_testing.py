import re
import pytest
import logging

from nomenclature.testing import assert_valid_yaml, assert_valid_structure
from conftest import TEST_DATA_DIR


def test_assert_yaml():
    """Check that importing a full-fledged (correct) nomenclature definition passes"""
    assert_valid_yaml(TEST_DATA_DIR / "validation_nc")


def test_assert_yaml_fails(caplog):
    """Check that parsing an invalid yaml raises expected error"""

    # assert that the expected error is raised
    match = "Parsing the yaml files failed. Please check the log for details."
    with pytest.raises(AssertionError, match=match):
        assert_valid_yaml(TEST_DATA_DIR / "invalid_yaml")

    # assert that the expected error message was written to the log
    log = caplog.record_tuples[0]
    assert log[0:2] == ("nomenclature.testing", logging.ERROR)

    obs = log[2].replace("\n", "")  # strip newlines from observed log message
    exp = r"Error parsing file while scanning a simple key.*, line 4, column 1"
    assert re.match(exp, obs)


def test_hidden_character():
    """Check that a non-printable character in any yaml file will raise an error"""
    match = "scenarios.yaml, line 3, col 12."
    with pytest.raises(AssertionError, match=match):
        assert_valid_yaml(TEST_DATA_DIR / "hidden_character")


def test_assert_valid_structure_requiredData_raises():

    with pytest.raises(ValueError) as e:
        assert_valid_structure(
            path=TEST_DATA_DIR / "required_data",
            definitions="definition",
            required_data="required_data",
        )
    # assert that all issues with requiredData files are reported correctly
    assert all(
        issue in str(e.value)
        for issue in (
            # 1. issue
            "requiredData_unknown_region.yaml",
            "region(s) were not found",
            "Asia",
            # 2. issue
            "requiredData_unknown_unit.yaml",
            "wrong unit",
            "('Final Energy', 'Mtoe/yr', 'EJ/yr')",
            # 3. issue
            "requiredData_unknown_variable.yaml",
            "variable(s) were not found",
            "Final Energy|Industry",
        )
    )
