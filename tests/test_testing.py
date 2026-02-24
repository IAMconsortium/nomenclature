import pytest
from conftest import TEST_DATA_DIR
from yaml.scanner import ScannerError

from nomenclature.exceptions import (
    ProcessorErrorGroup,
    UnknownRegionError,
    UnknownVariableError,
    WrongUnitError,
    YamlErrorGroup,
)
from nomenclature.testing import assert_valid_structure, assert_valid_yaml


def test_assert_yaml():
    """Check that importing a full-fledged (correct) nomenclature definition passes"""
    assert_valid_yaml(TEST_DATA_DIR / "data_structure_definition" / "validation_nc")


def test_assert_yaml_fails():
    """Check that parsing an invalid yaml raises expected error"""

    # Assert that the expected error is raised
    with pytest.raises(YamlErrorGroup, match="Parsing yaml files failed") as excinfo:
        assert_valid_yaml(TEST_DATA_DIR / "cli" / "invalid_yaml")
    assert excinfo.group_contains(
        ScannerError,
        match=r"while scanning a simple key\n.*\n.*\n.* line 4, column 1",
    )


def test_hidden_character():
    """Check that a non-printable character in any yaml file will raise an error"""
    with pytest.RaisesGroup(
        AssertionError, match="Parsing yaml files failed"
    ) as excinfo:
        assert_valid_yaml(TEST_DATA_DIR / "codelist" / "hidden_character")
    match = "scenarios.yaml, line 3, col 12."
    assert excinfo.group_contains(AssertionError, match=match)


def test_assert_valid_structure_requiredData_raises():
    with pytest.raises(ProcessorErrorGroup) as excinfo:
        assert_valid_structure(
            path=TEST_DATA_DIR / "required_data",
            definitions="definition",
            required_data="required_data",
        )
    # Assert that all issues with requiredData files are reported correctly
    assert len(excinfo.value.exceptions) == 5
    assert excinfo.group_contains(
        UnknownRegionError, match=r"region\(s\) are not defined.*\n.*Asia"
    )
    assert excinfo.group_contains(
        WrongUnitError,
        match=r"wrong unit:\n - 'Final Energy' - expected: 'EJ/yr', found: 'Mtoe/yr'",
    )
    assert excinfo.group_contains(
        UnknownVariableError,
        match=r"variable\(s\) are not defined.*\n - Final Energy\|Industry",
    )
