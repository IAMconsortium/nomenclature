import pytest
import pandas as pd
import nomenclature as nc

from conftest import TEST_DATA_DIR


def test_nonexisting_path_raises():
    """Check that initializing a Nomenclature with a non-existing path raises"""
    match = "Definitions directory not found: foo"
    with pytest.raises(NotADirectoryError, match=match):
        nc.Nomenclature("foo")


def test_to_excel(simple_nomenclature, tmpdir):
    """Check writing a nomenclature to file"""
    file = tmpdir / "testing_export.xlsx"
    simple_nomenclature.to_excel(file)

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "validation_nc.xlsx")
    pd.testing.assert_frame_equal(obs, exp)
