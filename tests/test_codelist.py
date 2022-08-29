import pytest
from pydantic import ValidationError
import pandas as pd
import pandas.testing as pdt
from nomenclature import CodeList
from nomenclature.error.codelist import DuplicateCodeError

from conftest import TEST_DATA_DIR


def test_simple_codelist():
    """Import a simple codelist"""
    code = CodeList.from_directory("variable", TEST_DATA_DIR / "simple_codelist")

    assert "Some Variable" in code
    assert code["Some Variable"]["unit"] is None  # this is a dimensionless variable
    assert type(code["Some Variable"]["bool"]) == bool  # this is a boolean


def test_codelist_to_yaml():
    """Cast a codelist to yaml format"""
    code = CodeList.from_directory("variable", TEST_DATA_DIR / "simple_codelist")

    assert code.to_yaml() == (
        "- Some Variable:\n"
        "    definition: Some basic variable\n"
        "    unit:\n"
        "    bool: true\n"
        "    file: simple_codelist/foo.yaml\n"
    )


def test_duplicate_code_raises():
    """Check that code conflicts across different files raises"""
    match = "Duplicate item in variable codelist: Some Variable"
    with pytest.raises(ValidationError, match=match):
        CodeList.from_directory("variable", TEST_DATA_DIR / "duplicate_code_raises")


def test_duplicate_tag_raises():
    """Check that code conflicts across different files raises"""
    match = "Duplicate item in tag codelist: Tag"
    with pytest.raises(DuplicateCodeError, match=match):
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


def test_norway_as_str():
    """guard against casting of 'NO' to boolean `False` by PyYAML or pydantic"""
    region = CodeList.from_directory("region", TEST_DATA_DIR / "norway_as_bool")
    assert region["Norway"]["eu_member"] is False
    assert region["Norway"]["iso2"] == "NO"


def test_to_excel(tmpdir):
    """Check writing to xlsx"""
    file = tmpdir / "foo.xlsx"

    (
        CodeList.from_directory(
            "Variable", TEST_DATA_DIR / "validation_nc" / "variable"
        ).to_excel(file)
    )

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "validation_nc.xlsx")

    pdt.assert_frame_equal(obs, exp)


def test_stray_tag_fails():
    """Check that typos in a tag raises expected error"""

    match = r"Unexpected {} in codelist: Primary Energy\|{Feul}"
    with pytest.raises(ValueError, match=match):
        CodeList.from_directory(
            "variable", TEST_DATA_DIR / "stray_tag" / "definitions" / "variable"
        )


def test_end_whitespace_fails():
    """Check that typos in a tag raises expected error"""

    match = "Unexpected whitespace at the end of a scenario code: 'scenario2 '"
    with pytest.raises(ValueError, match=match):
        CodeList.from_directory(
            "scenario", TEST_DATA_DIR / "end_whitespace" / "definitions" / "scenario"
        )
