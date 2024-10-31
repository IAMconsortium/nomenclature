import subprocess
import sys

import pandas as pd
import pydantic
import pytest

from click.testing import CliRunner
from pandas.testing import assert_frame_equal
from pyam import IAMC_IDX, IamDataFrame, assert_iamframe_equal

from nomenclature import cli
from nomenclature.testing import assert_valid_structure, assert_valid_yaml
from nomenclature.codelist import VariableCodeList

from conftest import TEST_DATA_DIR

MODULE_TEST_DATA_DIR = TEST_DATA_DIR / "cli"

runner = CliRunner()


@pytest.mark.xfail(
    sys.platform.startswith("win"),
    reason="Command to invoke the cli does not work on Windows",
)
def test_cli_installed():
    command = "poetry run nomenclature"
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=True,
        check=True,
    )
    assert all(
        command in result.stdout
        for command in (
            "check-region-aggregation",
            "export-definitions",
            "validate-project",
            "validate-yaml",
        )
    )


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
        cli,
        [
            "validate-yaml",
            str(TEST_DATA_DIR / "codelist" / "duplicate_code_raises"),
        ],
    )
    assert result_valid.exit_code == 0


def test_cli_valid_yaml_fails():
    """Check that CLI raises expected error when parsing an invalid yaml"""
    result_invalid = runner.invoke(
        cli, ["validate-yaml", str(MODULE_TEST_DATA_DIR / "invalid_yaml")]
    )
    assert result_invalid.exit_code == 1
    match = "Parsing the yaml files failed. Please check the log for details."
    with pytest.raises(AssertionError, match=match):
        assert_valid_yaml(MODULE_TEST_DATA_DIR / "invalid_yaml")


def test_cli_valid_project_path():
    """Check that CLI throws an error when the `path` is incorrect"""
    path = str(TEST_DATA_DIR / "incorrect_path")
    result_valid = runner.invoke(cli, ["validate-project", path])
    assert result_valid.exit_code == 2


def test_cli_valid_project():
    """Check that CLI runs through with existing "definitions" and "mappings"
    directory"""
    result_valid = runner.invoke(
        cli,
        [
            "validate-project",
            str(
                MODULE_TEST_DATA_DIR / "structure_validation",
            ),
        ],
    )
    assert result_valid.exit_code == 0


def test_cli_invalid_region():
    """Test that errors are correctly propagated"""
    obs = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "structure_validation_fails"),
        ],
    )
    assert obs.exit_code == 1
    assert isinstance(obs.exception, pydantic.ValidationError)
    assert "region_a" in obs.exception.errors()[0]["msg"]


def test_cli_valid_project_fails():
    """Check that CLI expected error when "definitions" directory doesn't exist"""
    path = TEST_DATA_DIR / "invalid_yaml" / "definitions"
    result_invalid = runner.invoke(
        cli, ["validate-project", str(MODULE_TEST_DATA_DIR / "invalid_yaml")]
    )
    assert result_invalid.exit_code == 1

    def print_helper(_path):
        print(f"Definitions directory not found: {_path}")

    with pytest.raises(NotADirectoryError, match=print_helper(path)):
        assert_valid_structure(
            MODULE_TEST_DATA_DIR / "invalid_yaml", "mappings", "definitions"
        )


def test_cli_non_default_folders():
    """Check that CLI runs through with non-default but existing "definitions" and
    "mappings" directory when the correct names are given"""
    result_valid = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "non-default_folders"),
            "--definitions",
            "def",
            "--mappings",
            "map",
        ],
    )
    assert result_valid.exit_code == 0


def test_cli_non_default_folders_fails():
    """Check that CLI raises expected error when non-default "definitions" and
    "mappings" directory names are not given"""
    result_valid = runner.invoke(
        cli,
        [
            "validate-project",
            str(
                MODULE_TEST_DATA_DIR / "non-default_folders",
            ),
        ],
    )
    assert result_valid.exit_code == 1


def test_cli_wrong_definitions_name():
    """Check that CLI raises expected error when a non-existing non-default directory
    is given"""
    result_valid = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "structure_validation"),
            "--definitions",
            "def",
        ],
    )
    assert result_valid.exit_code == 1


def test_cli_custom_dimensions_runs():
    """Check that CLI runs through when specifying a non-default dimension"""

    result_valid = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "non-default_dimensions"),
            "--dimension",
            "variable",
            "--dimension",
            "region",
            "--dimension",
            "scenario",
        ],
    )
    assert result_valid.exit_code == 0


def test_cli_custom_dimensions_fails():
    """Check that CLI raises an error when specifying a non-existing
    directory ('foo')"""

    result_invalid = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "non-default_dimensions"),
            "--dimension",
            "foo",
        ],
    )
    assert result_invalid.exit_code == 1
    assert isinstance(result_invalid.exception, ValueError)
    assert "Empty codelist: foo" in str(result_invalid.exception)


def test_cli_empty_dimensions_run():
    """Check that CLI runs through when an empty directory is not specified in
    custom dimensions"""

    result_valid = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "non-default_dimensions_one_empty"),
            "--dimension",
            "variable",
            "--dimension",
            "region",
        ],
    )
    assert result_valid.exit_code == 0


def test_cli_empty_dimensions_fails():
    """Check that CLI raises an error on an empty directory with default command"""

    result_invalid = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "non-default_dimensions_one_empty"),
        ],
    )
    assert result_invalid.exit_code == 1
    assert isinstance(result_invalid.exception, ValueError)
    assert "Empty codelist: empty" in str(result_invalid.exception)


def test_cli_missing_mappings_runs():
    """Assert that when **no** mappings folder is given by the user it's allowed
    to not exist"""

    assert (
        runner.invoke(
            cli,
            [
                "validate-project",
                str(MODULE_TEST_DATA_DIR / "structure_validation_no_mappings"),
            ],
        ).exit_code
        == 0
    )


def test_cli_missing_mappings_fails():
    """Assert that when a mappings folder is specified it needs to exist"""

    cli_result = runner.invoke(
        cli,
        [
            "validate-project",
            str(MODULE_TEST_DATA_DIR / "structure_validation_no_mappings"),
            "--mappings",
            "mappings",
        ],
    )

    assert cli_result.exit_code == 1
    assert isinstance(cli_result.exception, FileNotFoundError)
    assert "Mappings directory not found" in str(cli_result.exception)


def test_cli_validate_data_fails():
    """Assert that validating invalid yaml fails"""
    cli_result = runner.invoke(
        cli,
        [
            "validate-project",
            str(TEST_DATA_DIR / "validation"),
        ],
    )

    assert cli_result.exit_code == 1
    assert "Collected 5 errors" in str(cli_result.exception)
    assert "Asia" in str(cli_result.exception)
    assert "Final Energy|Industry" in str(cli_result.exception)


def test_cli_empty_definitions_dir():
    """Assert that an error is raised when the `definitions` directory is empty"""

    cli_result = runner.invoke(
        cli,
        ["validate-project", str(MODULE_TEST_DATA_DIR / "empty_definitions_dir")],
    )

    assert cli_result.exit_code == 1
    assert isinstance(cli_result.exception, FileNotFoundError)
    assert "`definitions` directory is empty" in str(cli_result.exception)


def test_check_region_aggregation(tmp_path):
    IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 5, 6],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    ).to_excel(tmp_path / "data.xlsx")
    runner.invoke(
        cli,
        [
            "check-region-aggregation",
            str(tmp_path / "data.xlsx"),
            "--workflow-directory",
            str(TEST_DATA_DIR / "region_processing"),
            "--definitions",
            "dsd",
            "--mappings",
            "partial_aggregation",
            "--processed-data",
            str(tmp_path / "results.xlsx"),
            "--differences",
            str(tmp_path / "differences.xlsx"),
        ],
    )

    # Check differences
    exp_difference = pd.DataFrame(
        [
            ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 2005, 5, 4, 20.0],
        ],
        columns=IAMC_IDX + ["year", "original", "aggregated", "difference (%)"],
    )
    assert_frame_equal(
        pd.read_excel(tmp_path / "differences.xlsx"), exp_difference, check_dtype=False
    )

    # Check aggregation result
    exp_result = IamDataFrame(
        pd.DataFrame(
            [["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 5, 6]],
            columns=IAMC_IDX + [2005, 2010],
        )
    )
    assert_iamframe_equal(IamDataFrame(tmp_path / "results.xlsx"), exp_result)


def test_cli_export_to_excel(tmpdir):
    """Assert that writing a DataStructureDefinition to excel works as expected"""
    file = tmpdir / "testing_export.xlsx"

    assert (
        runner.invoke(
            cli,
            [
                "export-definitions",
                str(TEST_DATA_DIR / "config" / "general-config"),
                str(file),
            ],
        ).exit_code
        == 0
    )

    with pd.ExcelFile(file) as obs:
        assert obs.sheet_names == ["project", "region", "variable"]


def test_cli_add_missing_variables(simple_definition, tmp_path):
    variable_code_list_path = tmp_path / "definitions" / "variable"
    variable_code_list_path.mkdir(parents=True)
    simple_definition.variable.to_yaml(variable_code_list_path / "variables.yaml")

    runner.invoke(
        cli,
        [
            "list-missing-variables",
            str(MODULE_TEST_DATA_DIR / "add-missing-variables" / "data.xlsx"),
            "--workflow-directory",
            str(tmp_path),
            "--target-file",
            "variables.yaml",
        ],
    )

    obs = VariableCodeList.from_directory(
        "variable", tmp_path / "definitions" / "variable"
    )

    assert "Some new variable" in obs
    assert obs["Some new variable"].unit == "EJ/yr"


def test_cli_run_workflow(tmp_path, simple_df):
    simple_df.to_excel(tmp_path / "input.xlsx")

    runner.invoke(
        cli,
        [
            "run-workflow",
            str(tmp_path / "input.xlsx"),
            "--workflow-file",
            str(TEST_DATA_DIR / "workflow" / "workflow.py"),
            "--output-file",
            str(tmp_path / "output.xlsx"),
        ],
    )

    assert_iamframe_equal(simple_df, IamDataFrame(tmp_path / "output.xlsx"))


@pytest.mark.parametrize(
    "status, unit, dimensions, exit_code",
    [
        ("valid_1", "EJ/yr", ["region", "variable"], 0),
        ("invalid", "EJ", "variable", 1),
        ("valid_2", "EJ", "region", 0),
    ],
)
def test_cli_valid_scenarios(status, unit, exit_code, dimensions, tmp_path):
    """Check that CLI validates an IAMC dataset according to defined codelists."""
    IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "World", "Primary Energy", unit, 1, 2],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    ).to_excel(tmp_path / f"{status}_data.xlsx")
    dimensions = [dimensions] if isinstance(dimensions, str) else dimensions
    dimension_args = []
    for dim in dimensions:
        dimension_args.append("--dimension")
        dimension_args.append(dim)

    result_valid = runner.invoke(
        cli,
        [
            "validate-scenarios",
            str(tmp_path / f"{status}_data.xlsx"),
            "--definitions",
            str(MODULE_TEST_DATA_DIR / "structure_validation" / "definitions"),
        ]
        + dimension_args,
    )
    assert result_valid.exit_code == exit_code


def test_cli_valid_scenarios_implicit_dimensions(tmp_path):
    """Check that CLI validates an IAMC dataset according to implicit dimensions codelists."""
    IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 1, 2],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    ).to_excel(tmp_path / "valid_data.xlsx")
    result_valid = runner.invoke(
        cli,
        [
            "validate-scenarios",
            str(tmp_path / "valid_data.xlsx"),
            "--definitions",
            str(MODULE_TEST_DATA_DIR / "structure_validation" / "definitions"),
        ],
    )
    assert result_valid.exit_code == 0
