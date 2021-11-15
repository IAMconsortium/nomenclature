import pytest
import pandas as pd
from nomenclature import DataStructureDefinition, create_yaml_from_xlsx

from conftest import TEST_DATA_DIR


def test_nonexisting_path_raises():
    """Check that initializing a DataStructureDefinition with a non-existing path
    raises"""
    match = "Definitions directory not found: foo"
    with pytest.raises(NotADirectoryError, match=match):
        DataStructureDefinition("foo")


def test_empty_codelist_raises():
    """Check that initializing a DataStructureDefinition with empty CodeList raises"""
    match = "Empty codelist: region, variable"
    with pytest.raises(ValueError, match=match):
        DataStructureDefinition(TEST_DATA_DIR / "simple_codelist")


def test_to_excel(simple_definition, tmpdir):
    """Check writing a DataStructureDefinition to file"""
    file = tmpdir / "testing_export.xlsx"

    simple_definition.to_excel(file)

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "validation_nc.xlsx")
    pd.testing.assert_frame_equal(obs, exp)


def test_create_yaml_from_xlsx(tmpdir):
    """Check that creating a yaml codelist from xlsx yields the expected output file"""
    file = tmpdir / "foo.yaml"

    create_yaml_from_xlsx(
        source=TEST_DATA_DIR / "validation_nc.xlsx",
        target=file,
        sheet_name="variable_definitions",
        col="Variable",
        attrs=["Definition", "Unit"],
    )

    with open(file, "r") as f:
        obs = f.read()
    with open(TEST_DATA_DIR / "validation_nc_flat.yaml", "r") as f:
        exp = f.read()

    assert obs == exp


def test_create_yaml_from_xlsx_duplicate():
    """Check that creating a yaml codelist from xlsx with duplicates raises"""
    with pytest.raises(ValueError, match="Duplicate values in the codelist:"):
        create_yaml_from_xlsx(
            source=TEST_DATA_DIR / "validation_nc_duplicates.xlsx",
            target="_",
            sheet_name="duplicate_index_raises",
            col="Variable",
            attrs=["Unit", "Definition"],
        )
