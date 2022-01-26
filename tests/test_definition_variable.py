import pytest
from nomenclature import DataStructureDefinition
from nomenclature.error.variable import (
    VariableRenameTargetError,
    VariableRenameArgError,
)

from conftest import TEST_DATA_DIR

TEST_FOLDER_VARIABLE = TEST_DATA_DIR / "failing_variable_codelist"


@pytest.mark.parametrize(
    "dir, error_type, error_msg_pattern",
    [
        (
            "rename_arg_conflict",
            VariableRenameArgError,
            ".*attribute 'region-aggregation' and arguments \['weight'\].*",
        ),
        (
            "rename_undefined_target",
            VariableRenameTargetError,
            "Region-aggregation-target\(s\) \['Price|Carbon (Max)'\] not defined.*",
        ),
    ],
)
def test_empty_codelist_raises(dir, error_type, error_msg_pattern):
    """Check that initializing a DataStructureDefinition raises expected errors"""
    with pytest.raises(error_type, match=error_msg_pattern):
        DataStructureDefinition(TEST_FOLDER_VARIABLE / dir, dimensions=["variable"])
