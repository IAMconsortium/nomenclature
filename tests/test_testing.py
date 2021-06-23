import re
import pytest
import logging

from nomenclature.testing import assert_valid_yaml
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
