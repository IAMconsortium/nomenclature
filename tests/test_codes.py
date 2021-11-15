import pytest
from nomenclature import CodeList

from conftest import TEST_DATA_DIR


def test_simple_codelist():
    """Import a simple codelist"""
    code = CodeList.from_directory("variable", TEST_DATA_DIR / "simple_codelist")

    assert "Some Variable" in code
    assert code["Some Variable"]["unit"] is None  # this is a dimensionless variable


def test_duplicate_code_raises():
    """Check that code conflicts across different files raises"""
    with pytest.raises(ValueError, match="Duplicate variable key: Some Variable"):
        CodeList.from_directory("variable", TEST_DATA_DIR / "duplicate_code_raises")


def test_duplicate_tag_raises():
    """Check that code conflicts across different files raises"""
    with pytest.raises(ValueError, match=r"Duplicate tag key: *"):
        CodeList.from_directory("variable", TEST_DATA_DIR / "duplicate_tag_raises")


def test_tagged_codelist():
    """Check that multiple tags in a code are correctly replaced"""
    code = CodeList.from_directory("variable", TEST_DATA_DIR / "tagged_codelist")

    v = "Final Energy|Industry|Renewables"
    d = "Final energy consumption of renewables in the industrial sector"
    assert v in code
    assert code[v]["definition"] == d


def test_region_codelist():
    """Check replacing top-level hierarchy of yaml file as attribute for regions"""
    code = CodeList.from_directory("region", TEST_DATA_DIR / "region_codelist")

    assert "World" in code
    assert code["World"]["hierarchy"] == "common"

    assert "Some Country" in code
    assert code["Some Country"]["hierarchy"] == "countries"
    assert code["Some Country"]["iso2"] == "XY"
