from pathlib import Path

import pandas as pd
import pytest
from conftest import TEST_DATA_DIR, clean_up_external_repos

from nomenclature import DataStructureDefinition
from nomenclature.cli import convert_xlsx_codelist_to_yaml
from nomenclature.code import Code


def test_definition_with_custom_dimension(simple_definition):
    """Check initializing a DataStructureDefinition with a custom dimension"""

    obs = DataStructureDefinition(
        TEST_DATA_DIR / "data_structure_definition" / "custom_dimension_nc",
        dimensions=["region", "variable", "scenario"],
    )

    # Check that "standard" dimensions are identical to simple test definitions
    assert obs.region == simple_definition.region
    assert obs.variable == simple_definition.variable

    # Check that "custom" dimensions are as expected
    assert obs.scenario["scen_a"] == Code(
        name="scen_a", extra_attributes={"attribute": "value"}
    )
    assert obs.scenario["scen_b"] == Code(name="scen_b")


def test_nonexisting_path_raises():
    """Check that initializing a DataStructureDefinition with non-existing path fails"""
    match = "Definitions directory not found: foo"
    with pytest.raises(NotADirectoryError, match=match):
        DataStructureDefinition("foo")


def test_empty_codelist_raises():
    """Check that initializing a DataStructureDefinition with empty CodeList raises"""
    match = "No dimensions specified."
    with pytest.raises(ValueError, match=match):
        DataStructureDefinition(TEST_DATA_DIR / "codelist" / "simple_codelist")


@pytest.mark.parametrize("workflow_folder", ["general-config-only", "general-config"])
def test_definition_from_general_config(workflow_folder):
    obs = DataStructureDefinition(
        TEST_DATA_DIR / "config" / workflow_folder / "definitions",
        dimensions=["region", "variable"],
    )
    try:
        # Explicitly defined in `general-config-definitions/region/regions.yaml`
        if workflow_folder == "general-config":
            assert "Region A" in obs.region
        # Imported from https://github.com/IAMconsortium/common-definitions
        assert "World" in obs.region

        # Imported from https://github.com/IAMconsortium/common-definitions
        assert "Primary Energy" in obs.variable
    finally:
        clean_up_external_repos(obs.config.repositories)


def test_definition_general_config_country_only():
    obs = DataStructureDefinition(
        TEST_DATA_DIR / "config" / "general-config-only-country" / "definitions"
    )
    assert all(region in obs.region for region in ("Austria", "Bolivia", "Kosovo"))


def test_definition_general_config_nuts_only():
    """Check that DataStructureDefinition is properly initialised with NUTS region config only"""
    obs = DataStructureDefinition(
        TEST_DATA_DIR / "config" / "general-config-only-nuts" / "definitions"
    )
    # Check country codes
    assert all(region[:2] in ("AT", "BE", "CZ") for region in obs.region)
    # Check region import
    assert len([region for region in obs.region if region.startswith("AT")]) == 4
    assert len([region for region in obs.region if region.startswith("BE")]) == 12
    assert len([region for region in obs.region if region.startswith("CZ")]) == 15


def test_to_excel(simple_definition, tmpdir):
    """Check writing a DataStructureDefinition to file"""
    file = tmpdir / "testing_export.xlsx"

    simple_definition.to_excel(file)

    obs = pd.read_excel(file, sheet_name="variable")
    exp = pd.read_excel(TEST_DATA_DIR / "io" / "excel_io" / "validation_nc.xlsx")
    pd.testing.assert_frame_equal(obs, exp)


def test_to_excel_with_external_repo(tmpdir):
    """Check writing a DataStructureDefinition with an external repo to file"""
    file = tmpdir / "testing_export.xlsx"

    try:
        dsd = DataStructureDefinition(
            TEST_DATA_DIR / "config" / "general-config" / "definitions"
        )
        dsd.to_excel(file)

        with pd.ExcelFile(file) as obs:
            assert obs.sheet_names == ["project", "region", "variable"]

            obs_project = obs.parse("project")
        exp = pd.DataFrame(
            [["project", "general-config"]], columns=["attribute", "value"]
        )
        pd.testing.assert_frame_equal(exp, obs_project[0:1])
    finally:
        clean_up_external_repos(dsd.config.repositories)


@pytest.mark.parametrize(
    "input_file, attrs, exp_file",
    [
        ("validation_nc.xlsx", ["description", "unit"], "validation_nc_flat.yaml"),
        (
            "validation_nc_list_arg.xlsx",
            ["description", "unit", "region-aggregation"],
            "validation_nc_list_arg.yaml",
        ),
    ],
)
def test_convert_xlsx_codelist_to_yaml(input_file, attrs, exp_file, tmpdir):
    """Check that creating a yaml codelist from xlsx yields the expected output file"""
    file = tmpdir / "foo.yaml"

    convert_xlsx_codelist_to_yaml(
        source=TEST_DATA_DIR / "io" / "excel_io" / input_file,
        target=file,
        sheet_name="variable_definitions",
        col="variable",
        attrs=attrs,
    )

    with open(file, "r", encoding="utf-8") as f:
        obs = f.read()
    with open(TEST_DATA_DIR / "io" / "excel_io" / exp_file, "r", encoding="utf-8") as f:
        exp = f.read()

    assert obs == exp


def test_convert_xlsx_codelist_to_yaml_duplicate():
    """Check that creating a yaml codelist from xlsx with duplicates raises"""
    with pytest.raises(ValueError, match="Duplicate values in the codelist:"):
        convert_xlsx_codelist_to_yaml(
            source=TEST_DATA_DIR / "io" / "excel_io" / "validation_nc_duplicates.xlsx",
            target=Path("_"),
            sheet_name="duplicate_index_raises",
            col="Variable",
            attrs=["Unit", "Description"],
        )
