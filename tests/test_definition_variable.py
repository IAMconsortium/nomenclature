import pytest
from pydantic import ValidationError
from nomenclature import DataStructureDefinition

from conftest import TEST_DATA_DIR

TEST_FOLDER_VARIABLE = TEST_DATA_DIR / "failing_variable_codelist"


@pytest.mark.parametrize(
    "dir, error_msg_pattern",
    [
        (
            "rename_arg_conflict",
            ".*attribute 'region-aggregation' and arguments \['weight'\].*",
        ),
        (
            "rename_undefined_target",
            "Region-aggregation-target\(s\) \['Price|Carbon (Max)'\] not defined.*",
        ),
    ],
)
def test_empty_codelist_raises(dir, error_msg_pattern):
    """Check that initializing a DataStructureDefinition raises expected errors"""
    with pytest.raises(ValidationError, match=error_msg_pattern):
        DataStructureDefinition(TEST_FOLDER_VARIABLE / dir, dimensions=["variable"])
