import shutil
import pytest
import pandas as pd
from nomenclature import DataStructureDefinition, create_yaml_from_xlsx
from nomenclature.code import Code

from conftest import TEST_DATA_DIR, clean_up_external_repos


def test_definition_with_custom_dimension(simple_definition):
    """Check initializing a DataStructureDefinition with a custom dimension"""

    obs = DataStructureDefinition(
        TEST_DATA_DIR / "custom_dimension_nc",
        dimensions=["region", "variable", "scenario"],
    )

    # check that "standard" dimensions are identical to simple test definitions
    assert obs.region == simple_definition.region
    assert obs.variable == simple_definition.variable

    # check that "custom" dimensions are as expected
    file = "scenario/scenarios.yaml"
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
    match = "Empty codelist: region, variable"
    with pytest.raises(ValueError, match=match):
        DataStructureDefinition(TEST_DATA_DIR / "simple_codelist")


def test_definition_from_general_config():
    obs = DataStructureDefinition(
        TEST_DATA_DIR / "general-config" / "definitions",
        dimensions=["region", "variable"],
    )
    try:
        # explicitly defined in `general-config-definitions/region/regions.yaml`
        assert "Region A" in obs.region
        # imported from https://github.com/IAMconsortium/common-definitions repo
        assert "World" in obs.region
        # added via general-config definitions
        assert "Austria" in obs.region
        # added via general-config definitions renamed from pycountry name
        assert "Bolivia" in obs.region
        # added via general-config definitions in addition to pycountry.countries
        assert "Kosovo" in obs.region

        # imported from https://github.com/IAMconsortium/common-definitions repo
        assert "Primary Energy" in obs.variable
    finally:
        clean_up_external_repos(obs.config.repositories)


def test_to_excel(simple_definition, tmpdir):
    """Check writing a DataStructureDefinition to file"""
    file = tmpdir / "testing_export.xlsx"

    simple_definition.to_excel(file)

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "excel_io" / "validation_nc.xlsx")
    pd.testing.assert_frame_equal(obs, exp)


@pytest.mark.parametrize(
    "input_file, attrs, exp_file",
    [
        ("validation_nc.xlsx", ["Description", "Unit"], "validation_nc_flat.yaml"),
        (
            "validation_nc_list_arg.xlsx",
            ["Description", "Unit", "Region-aggregation"],
            "validation_nc_list_arg.yaml",
        ),
    ],
)
def test_create_yaml_from_xlsx(input_file, attrs, exp_file, tmpdir):
    """Check that creating a yaml codelist from xlsx yields the expected output file"""
    file = tmpdir / "foo.yaml"

    create_yaml_from_xlsx(
        source=TEST_DATA_DIR / "excel_io" / input_file,
        target=file,
        sheet_name="variable_definitions",
        col="Variable",
        attrs=attrs,
    )

    with open(file, "r") as f:
        obs = f.read()
    with open(TEST_DATA_DIR / "excel_io" / exp_file, "r") as f:
        exp = f.read()

    assert obs == exp


def test_create_yaml_from_xlsx_duplicate():
    """Check that creating a yaml codelist from xlsx with duplicates raises"""
    with pytest.raises(ValueError, match="Duplicate values in the codelist:"):
        create_yaml_from_xlsx(
            source=TEST_DATA_DIR / "excel_io" / "validation_nc_duplicates.xlsx",
            target="_",
            sheet_name="duplicate_index_raises",
            col="Variable",
            attrs=["Unit", "Description"],
        )
