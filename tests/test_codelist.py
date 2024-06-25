from pytest import raises
import pandas as pd
import pandas.testing as pdt
import pytest
import logging

from nomenclature.code import Code, RegionCode, MetaCode
from nomenclature.codelist import (
    CodeList,
    VariableCodeList,
    RegionCodeList,
    MetaCodeList,
)
from nomenclature.config import NomenclatureConfig

from conftest import TEST_DATA_DIR, clean_up_external_repos


def test_simple_codelist():
    """Import a simple codelist"""
    codelist = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "simple_codelist"
    )

    assert "Some Variable" in codelist
    assert codelist["Some Variable"].unit is None  # this is a dimensionless variable
    assert type(codelist["Some Variable"].bool) == bool  # this is a boolean


def test_codelist_adding_duplicate_raises():
    codelist = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "simple_codelist"
    )
    with raises(ValueError, match="Duplicate item in variable codelist: Some Variable"):
        codelist["Some Variable"] = ""


def test_codelist_adding_non_code_raises():
    codelist = CodeList(name="test")

    with raises(TypeError, match="Codelist can only contain Code items"):
        codelist["Some Variable"] = ""


def test_codelist_name_key_mismatch():
    codelist = CodeList(name="test")

    with raises(ValueError, match="Key has to be equal to code name"):
        codelist["Some Variable"] = Code(name="Some other variable")


def test_codelist_to_yaml():
    """Cast a codelist to yaml format"""
    code = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "simple_codelist"
    )

    assert code.to_yaml() == (
        "- Some Variable:\n"
        "    description: Some basic variable\n"
        "    file: simple_codelist/foo.yaml\n"
        "    unit:\n"
        "    skip-region-aggregation: false\n"
        "    bool: true\n"
    )


def test_duplicate_code_raises():
    """Check that code conflicts across different files raises"""
    match = "Conflicting duplicate items in 'variable' codelist: 'Some Variable'"
    with raises(ValueError, match=match):
        VariableCodeList.from_directory(
            "variable", TEST_DATA_DIR / "duplicate_code_raises"
        )


def test_duplicate_tag_raises():
    """Check that code conflicts across different files raises"""
    match = "Duplicate item in tag codelist: Tag"
    with raises(ValueError, match=match):
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


def test_tags_in_list_attributes():
    """Test that tags are replaced correctly in list attributes"""
    code = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "tagged_codelist"
    )
    # The test should test that the tags in the definitions in the
    # tagged_codelist/foo_attr_list_dict.yaml file are expanded correctly.

    exp = {
        "Emissions|Species": {
            "description": "Emissions of Species",
            "unit": "tSpecies/yr",
        },
        "Emissions|CO2": {
            "description": "Total emissions of CO2",
            "unit": "tCO2/yr",
            "check_aggregate": True,
            "components": {
                "By source": ["Emissions|CO2|Fossil", "Emissions|CO2|Renewables"],
                "By sector": ["Emissions|CO2|Energy", "Emissions|CO2|Industry"],
            },
        },
        "Emissions|CH4": {
            "description": "Total emissions of CH4",
            "unit": "tCH4/yr",
            "check_aggregate": True,
            "components": {
                "By source": ["Emissions|CH4|Fossil", "Emissions|CH4|Renewables"],
                "By sector": ["Emissions|CH4|Energy", "Emissions|CH4|Industry"],
            },
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
            "variable", TEST_DATA_DIR / "validation_nc" / "variable"
        ).to_excel(file)
    )

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "excel_io" / "validation_nc.xlsx")

    pdt.assert_frame_equal(obs, exp)


def test_to_csv():
    """Check writing to csv"""
    obs = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "simple_codelist"
    ).to_csv(lineterminator="\n")

    exp = (
        "variable,description,unit,skip-region-aggregation,bool\n"
        "Some Variable,Some basic variable,,False,True\n"
    )
    assert obs == exp


def test_stray_tag_fails():
    """Check that typos in a tag raises expected error"""

    match = r"Unexpected {} in codelist: Primary Energy\|{Feul}"
    with raises(ValueError, match=match):
        VariableCodeList.from_directory(
            "variable", TEST_DATA_DIR / "stray_tag" / "definitions" / "variable"
        )


def test_end_whitespace_fails():
    """Check that typos in a tag raises expected error"""

    match = "Unexpected whitespace at the end of a scenario code: 'scenario2 '"
    with raises(ValueError, match=match):
        CodeList.from_directory(
            "scenario", TEST_DATA_DIR / "end_whitespace" / "definitions" / "scenario"
        )


def test_variable_codelist_units():
    """Check that the units-attribute works as expected"""
    codelist = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "validation_nc" / "variable"
    )
    assert codelist.units == ["", "EJ/yr"]


def test_variable_codelist_multiple_units():
    """Check that multiple units work in a VariableCodeList"""
    codelist = VariableCodeList.from_directory(
        "variable", TEST_DATA_DIR / "multiple_unit_codelist"
    )
    assert codelist["Var1"].unit == ["unit1", "unit2"]
    assert codelist.units == ["unit1", "unit2"]


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
        "variable",
        attrs=["description", "unit", "region-aggregation"],
    )

    assert obs == exp


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

    assert obs == exp


def test_RegionCodeList_filter():
    """Test that verifies the hierarchy filter can sort through list of regions and
    give list of regions contained in the given hierarchy"""

    # read RegionCodeList
    rcl = RegionCodeList.from_directory(
        "Region", TEST_DATA_DIR / "region_to_filter_codelist"
    )
    obs = rcl.filter(hierarchy="countries")

    mapping = {
        "Some Country": RegionCode(
            name="Some Country", description="some small country", hierarchy="countries"
        ),
        "Another Country": RegionCode(
            name="Another Country",
            description="another small country",
            hierarchy="countries",
        ),
    }
    exp = RegionCodeList(name=rcl.name, mapping=mapping)
    assert obs == exp


def test_RegionCodeList_hierarchy():
    """Verifies that the hierarchy method returns a List[str]"""

    rcl = RegionCodeList.from_directory(
        "Region", TEST_DATA_DIR / "region_to_filter_codelist"
    )
    assert rcl.hierarchy == ["common", "countries"]


def test_codelist_general_filter():
    var = CodeList.from_directory("Variable", TEST_DATA_DIR / "general_filtering")
    obs = var.filter(required=True)
    mapping = {
        "Big Variable": Code(
            name="Big Variable",
            description="Some basic variable",
            extra_attributes={
                "required": True,
            },
        )
    }
    exp = CodeList(name=var.name, mapping=mapping)
    assert obs == exp


def test_codelist_general_filter_multiple_attributes():
    var = CodeList.from_directory("Variable", TEST_DATA_DIR / "general_filtering")
    obs = var.filter(some_attribute=True, another_attribute="This is true")
    mapping = {
        "Another Variable": Code(
            name="Another Variable",
            description="some details",
            extra_attributes={
                "some_attribute": True,
                "another_attribute": "This is true",
            },
        )
    }
    exp = CodeList(name=var.name, mapping=mapping)
    assert obs == exp


def test_codelist_general_filter_No_Elements(caplog):
    var = CodeList.from_directory("Variable", TEST_DATA_DIR / "general_filtering")
    caplog.set_level(logging.WARNING)
    with caplog.at_level(logging.WARNING):
        obs = var.filter(
            some_attribute=True, another_attribute="This is true", required=False
        )
        assert obs == CodeList(name="Variable", mapping={})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[0].message == "Filtered CodeList is empty!"


def test_MetaCodeList_from_directory():
    obs = MetaCodeList.from_directory("Meta", TEST_DATA_DIR / "meta")
    mapping = {
        "exclude": MetaCode(
            name="exclude",
            description=None,
            allowed_values=[True, False],
        ),
        "Meta cat with int values": MetaCode(
            name="Meta cat with int values",
            description=None,
            allowed_values=[1, 2, 3],
        ),
    }
    exp = MetaCodeList(name="Meta", mapping=mapping)
    assert obs == exp


def test_multiple_external_repos():
    nomenclature_config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "nomenclature_configs" / "multiple_repos_per_dimension.yaml"
    )
    try:
        variable_code_list = VariableCodeList.from_directory(
            "variable",
            TEST_DATA_DIR / "nomenclature_configs" / "variable",
            nomenclature_config,
        )
        assert nomenclature_config.repositories.keys() == {
            "common-definitions",
            "legacy-definitions",
        }

        assert all(
            repo.local_path.is_dir()
            for repo in nomenclature_config.repositories.values()
        )
        assert len(variable_code_list) > 2000
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


def test_multiple_external_repos():
    nomenclature_config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "nomenclature_configs" / "multiple_repos_per_dimension.yaml"
    )
    try:
        variable_code_list = VariableCodeList.from_directory(
            "variable",
            TEST_DATA_DIR / "nomenclature_configs" / "variable",
            nomenclature_config,
        )
        assert variable_code_list["Final Energy"].repository == "common-definitions"
        assert variable_code_list["Employment"].repository == "legacy-definitions"
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


@pytest.mark.parametrize("CodeList", [VariableCodeList, CodeList])
def test_variable_codelist_with_duplicates_raises(CodeList):
    error_string = (
        "2 errors:\n.*Identical.*'Some Variable'.*\n.*\n.*\n.*Conflicting."
        "*'Some other Variable'"
    )
    with raises(ValueError, match=error_string):
        CodeList.from_directory(
            "variable", TEST_DATA_DIR / "duplicate-code-list" / "variable"
        )
