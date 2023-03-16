import pytest
import pandas as pd
import pandas.testing as pdt
from nomenclature.code import Code
from nomenclature.codelist import CodeList, VariableCodeList, RegionCodeList
from nomenclature.error.codelist import DuplicateCodeError

from conftest import TEST_DATA_DIR, remove_file_from_mapping


def test_simple_codelist():
    """Import a simple codelist"""
    code = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "simple_codelist"
    )

    assert "Some Variable" in code
    assert code["Some Variable"].unit is None  # this is a dimensionless variable
    assert type(code["Some Variable"].bool) == bool  # this is a boolean


def test_codelist_to_yaml():
    """Cast a codelist to yaml format"""
    code = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "simple_codelist"
    )

    assert code.to_yaml() == (
        "- Some Variable:\n"
        "    description: Some basic variable\n"
        "    unit:\n"
        "    skip-region-aggregation: false\n"
        "    check-aggregate: false\n"
        "    bool: true\n"
        "    file: simple_codelist/foo.yaml\n"
    )


def test_duplicate_code_raises():
    """Check that code conflicts across different files raises"""
    match = "Duplicate item in variable codelist: Some Variable"
    with pytest.raises(DuplicateCodeError, match=match):
        VariableCodeList.from_directory(
            "variable", TEST_DATA_DIR / "duplicate_code_raises"
        )


def test_duplicate_tag_raises():
    """Check that code conflicts across different files raises"""
    match = "Duplicate item in tag codelist: Tag"
    with pytest.raises(DuplicateCodeError, match=match):
        VariableCodeList.from_directory(
            "variable", TEST_DATA_DIR / "duplicate_tag_raises"
        )


def test_tagged_codelist():
    """Check that multiple tags in a code are correctly replaced"""
    code = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "tagged_codelist"
    )

    exp = {
        "Final Energy|Industry|Renewables": {
            "description": (
                "Final energy consumption of renewables in the industrial sector"
            ),
            "weight": "Final Energy|Industry",
        },
        "Final Energy|Energy|Renewables": {
            "description": (
                "Final energy consumption of renewables in the energy sector"
            ),
            "weight": "Final Energy|Energy",
        },
    }

    for code_name, attrs in exp.items():
        assert code_name in code
        for attr_name, value in attrs.items():
            assert getattr(code[code_name], attr_name) == value


def test_region_codelist():
    """Check replacing top-level hierarchy of yaml file as attribute for regions"""
    code = RegionCodeList.from_directory("region", TEST_DATA_DIR / "region_codelist")

    assert "World" in code
    assert code["World"].hierarchy == "common"

    assert "Some Country" in code
    assert code["Some Country"].hierarchy == "countries"
    assert code["Some Country"].iso2 == "XY"


def test_norway_as_str():
    """guard against casting of 'NO' to boolean `False` by PyYAML or pydantic"""
    region = RegionCodeList.from_directory("region", TEST_DATA_DIR / "norway_as_bool")
    assert region["Norway"].eu_member is False
    assert region["Norway"].iso2 == "NO"


def test_to_excel(tmpdir):
    """Check writing to xlsx"""
    file = tmpdir / "foo.xlsx"

    (
        VariableCodeList.from_directory(
            "Variable", TEST_DATA_DIR / "validation_nc" / "variable"
        ).to_excel(file)
    )

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "validation_nc.xlsx")

    pdt.assert_frame_equal(obs, exp)


@pytest.mark.parametrize("sort", (True, False))
def test_to_csv(sort):
    """Check writing to csv"""
    obs = VariableCodeList.from_directory(
        "Variable", TEST_DATA_DIR / "simple_codelist"
    ).to_csv(sort_by_code=sort, lineterminator="\n")

    exp = (
        "Variable,Description,Unit,Skip-region-aggregation,Check-aggregate,Bool\n"
        "Some Variable,Some basic variable,,False,False,True\n"
    )
    assert obs == exp


def test_stray_tag_fails():
    """Check that typos in a tag raises expected error"""

    match = r"Unexpected {} in codelist: Primary Energy\|{Feul}"
    with pytest.raises(ValueError, match=match):
        VariableCodeList.from_directory(
            "variable", TEST_DATA_DIR / "stray_tag" / "definitions" / "variable"
        )


def test_end_whitespace_fails():
    """Check that typos in a tag raises expected error"""

    match = "Unexpected whitespace at the end of a scenario code: 'scenario2 '"
    with pytest.raises(ValueError, match=match):
        CodeList.from_directory(
            "scenario", TEST_DATA_DIR / "end_whitespace" / "definitions" / "scenario"
        )


def test_variable_codelist_multiple_units():
    """Check that multiple units work in a VariableCodeList"""
    codelist = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "multiple_unit_codelist"
    )
    assert codelist["Var1"].unit == ["unit1", "unit2"]


def test_to_excel_read_excel_roundtrip(tmpdir):
    codelist_dir = TEST_DATA_DIR / "variable_codelist_complex_attr"

    # read VariableCodeList
    exp = VariableCodeList.from_directory("variable", codelist_dir)
    # save to temporary file
    exp.to_excel(tmpdir / "output.xlsx")
    # read from temporary file
    obs = VariableCodeList.read_excel(
        "variable",
        tmpdir / "output.xlsx",
        "variable",
        "Variable",
        attrs=["Description", "Unit", "Region-aggregation"],
    )

    assert obs.name == exp.name
    # since the obs and exp are read from different files, the file attribute will be
    # different. For comparison we remove it
    assert remove_file_from_mapping(obs.mapping) == remove_file_from_mapping(
        exp.mapping
    )


def test_to_yaml_from_directory(tmp_path):
    """Test that creating a codelist from a yaml file and writing it to yaml produces
    the same file"""

    # read VariableCodeList
    exp = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "variable_codelist_complex_attr"
    )
    exp.to_yaml(tmp_path / "variables.yaml")

    # read from temporary file
    obs = VariableCodeList.from_directory("variable", tmp_path)

    assert obs.name == exp.name
    # since the obs and exp are read from different files, the file attribute will be
    # different. For comparison we remove it
    assert remove_file_from_mapping(obs.mapping) == remove_file_from_mapping(
        exp.mapping
    )


def test_RegionCodeList_filter():
    """Test that verifies the hierarchy filter can sort through list of regions and
    give list of regions contained in the given hierarchy"""

    # read RegionCodeList
    rcl = RegionCodeList.from_directory("Region", TEST_DATA_DIR / "region_codelist")
    obs = rcl.filter("countries")
    extra_attributes = {
        "iso2": "XY",
        "iso3": "XYZ",
        "hierarchy": "countries",
        "file": "region_codelist/region.yaml",
    }
    mapping = {
        "Some Country": Code(
            name="Some Country", description=None, extra_attributes=extra_attributes
        )
    }
    exp = RegionCodeList(name=rcl.name, mapping=mapping)
    assert obs == exp


def test_RegionCodeList_filter_ValueError():
    """Test that verifies the filter gives error when user inputs an unrecognizeable
    hierarchy"""

    # read RegionCodeList
    rcl = RegionCodeList.from_directory("Region", TEST_DATA_DIR / "region_codelist")
    match = (
        "Filtered RegionCodeList is empty: hierarchy=R77\n"
        "Use `RegionCodeList.hierarchy` for available items."
    )
    with pytest.raises(ValueError, match=match):
        rcl.filter("R77")


def test_RegionCodeList_hierarchy_one_option():
    """Verifies that when only one hierarchy available, hierarchy() returns
    str specifying that hierarchy"""

    rcl = RegionCodeList.from_directory("Region", TEST_DATA_DIR / "region_codelist_one")
    match = "Option available: common"
    assert rcl.hierarchy == match


def test_RegionCodeList_hierarchy_two_options():
    """Verifies that when there are two hierarchies available, hierarchy() returns
    str specifying them with only an 'and' in between"""

    rcl = RegionCodeList.from_directory("Region", TEST_DATA_DIR / "region_codelist")
    match = "Options available: common and countries"
    assert rcl.hierarchy == match


def test_RegionCodeList_hierarchy_four_options():
    """Verifies that when there are more than three hierarchies available,
    hierarchy() returns str specifying them with commas and an 'and' in between
    the last hierarchies"""

    rcl = RegionCodeList.from_directory(
        "Region", TEST_DATA_DIR / "region_codelist_four"
    )
    match = (
        "Options available: First Region, Fourth Region, Second Region and Third Region"
    )
    assert rcl.hierarchy == match
