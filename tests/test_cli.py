from click.testing import CliRunner
from nomenclature.testing import cli, assert_valid_yaml, check_valid_structure
import pytest

from conftest import TEST_DATA_DIR

runner = CliRunner()


def test_cli_valid_yaml_path():
    """Check that CLI throws an error when the `path` is incorrect"""
    result_valid = runner.invoke(
        cli, ["validate-yaml", str(TEST_DATA_DIR / "incorrect_path")]
    )
    assert result_valid.exit_code == 2


def test_cli_valid_yaml():
    """Check that CLI runs through, when all yaml files in `path`
    can be parsed without errors"""
    result_valid = runner.invoke(
        cli, ["validate-yaml", str(TEST_DATA_DIR / "duplicate_code_raises")]
    )
    assert result_valid.exit_code == 0


def test_cli_valid_yaml_fails():
    """Check that CLI raises expected error when parsing an invalid yaml"""
    result_invalid = runner.invoke(
        cli, ["validate-yaml", str(TEST_DATA_DIR / "invalid_yaml")]
    )
    assert result_invalid.exit_code == 1
    match = "Parsing the yaml files failed. Please check the log for details."
    with pytest.raises(AssertionError, match=match):
        assert_valid_yaml(TEST_DATA_DIR / "invalid_yaml")


def test_cli_valid_structure_path():
    """Check that CLI throws an error when the `path` is incorrect"""
    path = str(TEST_DATA_DIR / "incorrect_path")
    result_valid = runner.invoke(cli, ["validate-project", path])
    assert result_valid.exit_code == 2


def test_cli_valid_structure():
    """Check that CLI runs through with existing "definitions" directory"""
    result_valid = runner.invoke(
        cli, ["validate-project", str(TEST_DATA_DIR / "structure_validation")]
    )
    assert result_valid.exit_code == 0


def test_cli_valid_structure_fails():
    """Check that CLI expected error when "definitions" directory doesn't exist"""
    path = TEST_DATA_DIR / "invalid_yaml" / "definitions"
    result_invalid = runner.invoke(
        cli, ["validate-project", str(TEST_DATA_DIR / "invalid_yaml")]
    )
    assert result_invalid.exit_code == 1

    def print_helper(path_input):
        print(f"Definitions directory not found: {path_input}")

    with pytest.raises(NotADirectoryError, match=print_helper(path)):
        check_valid_structure(TEST_DATA_DIR / "invalid_yaml")
