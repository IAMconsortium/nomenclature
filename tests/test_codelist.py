import logging

import pandas as pd
import pandas.testing as pdt
import pytest
from conftest import TEST_DATA_DIR, clean_up_external_repos
from pytest import RaisesGroup, raises

from nomenclature.code import Code, MetaCode, RegionCode, VariableCode
from nomenclature.codelist import (
    CodeList,
    MetaCodeList,
    RegionCodeList,
    VariableCodeList,
)
from nomenclature.config import NomenclatureConfig
from nomenclature.definition import DataStructureDefinition

MODULE_TEST_DATA_DIR = TEST_DATA_DIR / "codelist"


def test_simple_codelist():
    """Import a simple codelist"""
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "simple_codelist"
    )

    assert "Some Variable" in variables
    assert variables["Some Variable"].unit == ""  # this is a dimensionless variable
    assert type(variables["Some Variable"].bool) is bool  # this is a boolean


def test_codelist_adding_duplicate_raises():
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "simple_codelist"
    )
    with raises(ValueError, match="Duplicate item in variable codelist: Some Variable"):
        variables["Some Variable"] = ""


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
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "simple_codelist"
    )

    assert variables.to_yaml() == (
        "- Some Variable:\n"
        "    description: Some basic variable\n"
        "    file: simple_codelist/foo.yaml\n"
        "    unit:\n"
        "    skip-region-aggregation: false\n"
        "    bool: true\n"
    )


def test_duplicate_code_raises():
    """Check that code conflicts across different files raises"""

    with RaisesGroup(ValueError, match="Found errors in codelist") as excinfo:
        VariableCodeList.from_directory(
            "variable", MODULE_TEST_DATA_DIR / "duplicate_code_raises"
        )
    assert excinfo.group_contains(
        ValueError, match="duplicate items in 'variable' codelist: 'Some Vari"
    )


def test_duplicate_tag_raises():
    """Check that code conflicts across different files raises"""
    match = "Duplicate item in tag codelist: Tag"
    with raises(ValueError, match=match):
        VariableCodeList.from_directory(
            "variable", MODULE_TEST_DATA_DIR / "duplicate_tag_raises"
        )


def test_tagged_codelist():
    """Check that multiple tags in a code are correctly replaced"""
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "tagged_codelist"
    )

    exp = {
        "Final Energy|Industry|Renewables": {
            "description": (
                "Final energy consumption of renewables in the industrial sector"
            ),
            "weight": "Final Energy|Industry",
            "extra": 1,
        },
        "Final Energy|Energy|Renewables": {
            "description": (
                "Final energy consumption of renewables in the energy sector"
            ),
            "weight": "Final Energy|Energy",
        },
    }

    for code_name, attrs in exp.items():
        assert code_name in variables
        for attr_name, value in attrs.items():
            assert getattr(variables[code_name], attr_name) == value


def test_tags_in_list_attributes():
    """Test that tags are replaced correctly in list attributes"""
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "tagged_codelist"
    )
    # The test should test that the tags in the definitions in the
    # tagged_codelist/foo_attr_list_dict.yaml file are expanded correctly.

    exp = {
        "Emissions|CO2": {
            "description": "Total emissions of carbon dioxide (CO2)",
            "unit": "Mt CO2/yr",
            "check_aggregate": True,
            "components": {
                "By source": ["Emissions|CO2|Fossil", "Emissions|CO2|Renewables"],
                "By sector": ["Emissions|CO2|Energy", "Emissions|CO2|Industry"],
            },
        },
        "Emissions|CH4": {
            "description": "Total emissions of methane (CH4)",
            "unit": "Mt CH4/yr",
            "check_aggregate": True,
            "components": {
                "By source": ["Emissions|CH4|Fossil", "Emissions|CH4|Renewables"],
                "By sector": ["Emissions|CH4|Energy", "Emissions|CH4|Industry"],
            },
        },
    }

    for code_name, attrs in exp.items():
        assert code_name in variables
        for attr_name, value in attrs.items():
            assert getattr(variables[code_name], attr_name) == value


def test_tier_attribute_in_tags():
    """Check for tier attribute functionality ('tier' in tags increment CodeList):
    1) 'tier' is not added when not present in Code or tag;
    2) 'tier' is/are incremented when present in Code and matching tag(s)"""
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "tier_attribute" / "valid"
    )
    # Check tier attribute is incremented correctly
    assert variables["Final Energy|Coal|Industry"].tier == 1
    assert variables["Final Energy|Coal|Lignite|Industry"].tier == 2
    assert variables["Final Energy|Coal|Industry|Chemicals"].tier == 2
    assert variables["Primary Energy|Coal [Share]"].tier == 2
    assert variables["Primary Energy|Coal|Lignite [Share]"].tier == 3

    # Check multiple tier attributes increment cumulatively
    assert variables["Final Energy|Coal|Lignite|Industry|Chemicals"].tier == 3

    # Check codes without tier attributes don't change
    assert not variables["Primary Energy"].tier


def test_misformatted_tier_fails():
    """Check misformatted 'tier' attributes raise errors"""

    match = "Invalid 'tier' attribute in 'Fuel' tag 'Coal': 1\n"
    "Allowed values are '^1' or '^2'."
    with pytest.raises(ValueError, match=match):
        VariableCodeList.from_directory(
            "variable", MODULE_TEST_DATA_DIR / "tier_attribute" / "invalid"
        )


def test_region_codelist():
    """Check the attributes of a codes in a RegionCodeList (hierarchy, etc.)"""
    regions = RegionCodeList.from_directory(
        "region", MODULE_TEST_DATA_DIR / "region_codelist" / "simple"
    )

    assert "World" in regions
    assert regions["World"].hierarchy == "common"

    assert "Some Country" in regions
    code = regions["Some Country"]
    assert code.hierarchy == "countries"
    assert code.iso2 == "XY"
    assert not code.has_prefix
    assert code.prefix == ""
    assert not code.is_directional
    with pytest.raises(ValueError, match="Non-directional region does not have a des"):
        code.destination

    assert "Some Country>World" in regions
    code = regions["Some Country>World"]
    assert code.is_directional
    assert code.hierarchy == "directional"
    assert code.origin == "Some Country"
    assert code.destination == "World"


def test_region_codelist_nonexisting_country_name():
    """Check that countries are validated against `nomenclature.countries`"""
    with pytest.raises(ValueError, match="Region 'Some region' .*: Czech Republic"):
        RegionCodeList.from_directory(
            "region",
            MODULE_TEST_DATA_DIR
            / "region_codelist"
            / "countries_attribute_non-existing_name",
        )


def test_directional_region_codelist_nonexisting_country_name():
    """Check that directional regions have defined origin and destination"""
    with pytest.raises(ValueError, match="Destination 'Germany' .* 'Austria>Germany'"):
        RegionCodeList.from_directory(
            "region",
            MODULE_TEST_DATA_DIR
            / "region_codelist"
            / "directional_non-existing_component",
        )


def test_directional_model_specific_region_codelist():
    """Check that directional model-specific regions are parsed as expected"""
    regions = RegionCodeList.from_directory(
        "region",
        MODULE_TEST_DATA_DIR / "region_codelist" / "directional_model_specific",
    )

    code = regions["Model A|Region 1"]
    assert code.has_prefix
    assert code.prefix == "Model A"

    code = regions["Model A|Region 1>Region 2"]
    assert code.is_directional
    assert code.hierarchy == "Model A [directional]"
    assert code.origin == "Model A|Region 1"
    assert code.destination == "Model A|Region 2"


def test_region_codelist_str_country_name():
    """Check that country name as string is validated against `nomenclature.countries`"""
    regions = RegionCodeList.from_directory(
        "region",
        MODULE_TEST_DATA_DIR / "region_codelist" / "countries_attribute_str",
    )
    assert regions["Some region"].countries == ["Austria"]


def test_norway_as_str():
    """guard against casting of 'NO' to boolean `False` by PyYAML or pydantic"""
    regions = RegionCodeList.from_directory(
        "region",
        MODULE_TEST_DATA_DIR / "region_codelist" / "norway_as_bool",
    )
    assert regions["Norway"].eu_member is False
    assert regions["Norway"].iso2 == "NO"


def test_to_excel(tmpdir):
    """Check writing to xlsx"""
    file = tmpdir / "foo.xlsx"

    (
        VariableCodeList.from_directory(
            "variable",
            TEST_DATA_DIR / "data_structure_definition" / "validation_nc" / "variable",
        ).to_excel(file)
    )

    obs = pd.read_excel(file)
    exp = pd.read_excel(TEST_DATA_DIR / "io" / "excel_io" / "validation_nc.xlsx")

    pdt.assert_frame_equal(obs, exp)


def test_to_csv():
    """Check writing to csv"""
    obs = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "simple_codelist"
    ).to_csv(lineterminator="\n")

    exp = (
        "variable,description,unit,skip-region-aggregation,bool\n"
        "Some Variable,Some basic variable,,False,True\n"
    )
    assert obs == exp


@pytest.mark.parametrize(
    "subfolder, match",
    [
        (
            "tag_in_str",
            (
                "Illegal character\\(s\\) '{', '}' in 'name' of variable "
                "'Primary Energy|\\{Feul\\}'"
            ),
        ),
        (
            "tag_in_list",
            "Illegal character\\(s\\) '{' in 'info' of variable 'Share|Coal'",
        ),
        (
            "tag_in_dict",
            "Illegal character\\(s\\) '}' in 'invalid' of variable 'Primary Energy'",
        ),
    ],
)
def test_stray_tag_fails(subfolder, match):
    """Check that stray brackets from, e.g. typos in a tag, raises expected error"""
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "stray_tag" / subfolder
    )
    with pytest.raises(ExceptionGroup, match="Found illegal characters") as excinfo:
        variables.check_illegal_characters(NomenclatureConfig(dimensions=["variable"]))
    assert excinfo.group_contains(ValueError, match=match)


def test_illegal_chars_raise():
    """Check that illegal characters raise error if found."""
    match = "Illegal character(s) '\"' in info of variable 'Primary Energy|Coal'"
    with RaisesGroup(ValueError) as excinfo:
        DataStructureDefinition(
            MODULE_TEST_DATA_DIR / "illegal_chars" / "char_in_str" / "definitions"
        )
    assert excinfo.group_contains(ValueError, match=match)


def test_illegal_chars_ignore():
    """Check that illegal characters are ignored (don't raise) if not listed in config."""
    assert (
        DataStructureDefinition(
            MODULE_TEST_DATA_DIR / "illegal_chars" / "no_chars" / "definitions"
        ).config.illegal_characters
        == []
    )


def test_illegal_char_ignores_external_repo():
    """Check that external repos are excluded from this check."""
    # The config includes illegal characters known to be in common-definitions
    # The test will not raise errors as the check is skipped for external repos

    try:
        dsd = DataStructureDefinition(
            MODULE_TEST_DATA_DIR
            / "illegal_chars"
            / "char_in_external_repo"
            / "definitions"
        )
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_end_whitespace_fails():
    """Check that typos in a tag raises expected error"""

    with RaisesGroup(ValueError, match="Found trailing whitespace") as excinfo:
        CodeList.from_directory(
            "scenario",
            MODULE_TEST_DATA_DIR / "end_whitespace" / "definitions" / "scenario",
        )
    assert excinfo.group_contains(
        ValueError,
        match="Unexpected whitespace at the end of a scenario code: 'scenario2 '",
    )


def test_variable_codelist_units():
    """Check that the units-attribute works as expected"""
    variables = VariableCodeList.from_directory(
        "variable",
        TEST_DATA_DIR / "data_structure_definition" / "validation_nc" / "variable",
    )
    assert variables.units == ["", "EJ/yr"]


def test_variable_codelist_multiple_units():
    """Check that multiple units work in a VariableCodeList"""
    variables = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "multiple_unit_codelist"
    )
    assert variables["Var1"].unit == ["unit1", "unit2"]
    assert variables.units == ["unit1", "unit2"]


def test_to_excel_read_excel_roundtrip(tmpdir):
    codelist_dir = MODULE_TEST_DATA_DIR / "variable_codelist_complex_attr"

    # Read VariableCodeList
    exp = VariableCodeList.from_directory("variable", codelist_dir)
    # Save to temporary file
    exp.to_excel(tmpdir / "output.xlsx")
    # Read from temporary file
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

    # Read VariableCodeList
    exp = VariableCodeList.from_directory(
        "variable", MODULE_TEST_DATA_DIR / "variable_codelist_complex_attr"
    )
    exp.to_yaml(tmp_path / "variables.yaml")

    # Read from temporary file
    obs = VariableCodeList.from_directory("variable", tmp_path)

    assert obs == exp


def test_RegionCodeList_filter():
    """Test that verifies the hierarchy filter can sort through list of regions and
    give list of regions contained in the given hierarchy"""

    regions = RegionCodeList.from_directory(
        "Region", MODULE_TEST_DATA_DIR / "region_to_filter_codelist"
    )
    obs = regions.filter(hierarchy="countries")

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
    exp = RegionCodeList(name=regions.name, mapping=mapping)
    assert obs == exp


def test_RegionCodeList_hierarchy():
    """Verifies that the hierarchy method returns a list"""

    regions = RegionCodeList.from_directory(
        "Region", MODULE_TEST_DATA_DIR / "region_to_filter_codelist"
    )
    assert regions.hierarchy == ["common", "countries"]


def test_codelist_general_filter():
    codelist = CodeList.from_directory(
        "Variable", MODULE_TEST_DATA_DIR / "general_filtering"
    )
    obs = codelist.filter(required=True)
    mapping = {
        "Big Variable": Code(
            name="Big Variable",
            description="Some basic variable",
            extra_attributes={
                "required": True,
            },
        )
    }
    exp = CodeList(name=codelist.name, mapping=mapping)
    assert obs == exp


def test_codelist_general_filter_multiple_attributes():
    codelist = CodeList.from_directory(
        "Variable", MODULE_TEST_DATA_DIR / "general_filtering"
    )
    obs = codelist.filter(some_attribute=True, another_attribute="This is true")
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
    exp = CodeList(name=codelist.name, mapping=mapping)
    assert obs == exp


def test_codelist_general_filter_No_Elements(caplog):
    codelist = CodeList.from_directory(
        "Variable", MODULE_TEST_DATA_DIR / "general_filtering"
    )
    caplog.set_level(logging.WARNING)
    with caplog.at_level(logging.WARNING):
        obs = codelist.filter(
            some_attribute=True, another_attribute="This is true", required=False
        )
        assert obs == CodeList(name="Variable", mapping={})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[0].message == "Filtered CodeList is empty!"


def test_MetaCodeList_from_directory():
    obs = MetaCodeList.from_directory("Meta", MODULE_TEST_DATA_DIR / "meta")
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
        TEST_DATA_DIR / "config" / "multiple_repos_per_dimension.yaml"
    )
    try:
        variables = VariableCodeList.from_directory(
            "variable",
            TEST_DATA_DIR / "config" / "variable",
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
        assert len(variables) > 2000
        assert variables["Final Energy"].repository == "common-definitions"
        assert variables["Employment"].repository == "legacy-definitions"
    finally:
        clean_up_external_repos(nomenclature_config.repositories)


@pytest.mark.parametrize("CodeList", [VariableCodeList, CodeList])
def test_variable_codelist_with_duplicates_raises(CodeList):
    with RaisesGroup(
        ValueError, ValueError, match="Found errors in codelist"
    ) as excinfo:
        CodeList.from_directory(
            "variable", MODULE_TEST_DATA_DIR / "duplicate-code-list" / "variable"
        )

    assert excinfo.group_contains(ValueError, match="Identical.*'Some Variable'")
    assert excinfo.group_contains(
        ValueError, match="Conflicting." "*'Some other Variable'"
    )


def test_variablecodelist_list_missing_variables_to_new_file(simple_df, tmp_path):
    empty_variables = VariableCodeList(name="variable")
    empty_variables.list_missing_variables(
        simple_df,
        tmp_path / "variables.yaml",
    )

    obs = VariableCodeList.from_directory("variable", tmp_path)
    exp = {
        "Primary Energy": VariableCode(name="Primary Energy", unit="EJ/yr"),
        "Primary Energy|Coal": VariableCode(name="Primary Energy|Coal", unit="EJ/yr"),
    }

    assert obs.mapping == exp


@pytest.mark.parametrize(
    "codelist_filter",
    [None, {"name": ["Primary Energy*", "Final Energy*"], "tier": 2}],
)
def test_variable_code_list_external_repo_with_filters(codelist_filter):
    nomenclature_config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "config" / "external_repo_filters.yaml"
    )
    try:
        codelist = VariableCodeList.from_directory(
            "variable",
            TEST_DATA_DIR / "nomenclature_configs" / "variable",
            nomenclature_config,
        )
        exp_included_variables = [
            "Final Energy",
            "Population",
            "Primary Energy|Oil|Hydrogen|w/ CCS",
        ]
        exp_excluded_variables = [
            "Final Energy|Agriculture|Electricity",  # No third level Final Energy
            "Population|Clean Cooking Access",  # Only tier 1 Population
        ]
        assert all(variable in codelist for variable in exp_included_variables)
        assert all(variable not in codelist for variable in exp_excluded_variables)
    finally:
        clean_up_external_repos(nomenclature_config.repositories)

    if codelist_filter:
        filtered_codelist = codelist.filter(**codelist_filter)
        assert all(code.tier == 2 for code in filtered_codelist.mapping.values())
        assert any(
            code.name.startswith(("Primary Energy", "Final Energy"))
            for code in filtered_codelist.mapping.values()
        )
        assert not any(
            code.name.startswith("Population")
            for code in filtered_codelist.mapping.values()
        )


def test_region_code_list_external_repo_with_filters():
    nomenclature_config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "config" / "external_repo_filters.yaml"
    )
    try:
        regions = RegionCodeList.from_directory(
            "region",
            TEST_DATA_DIR / "config" / "variable",
            nomenclature_config,
        )
        R5_regions = [
            "OECD & EU (R5)",
            "Reforming Economies (R5)",
            "Asia (R5)",
            "Middle East & Africa (R5)",
            "Latin America (R5)",
        ]
        assert len(regions) == 5
        assert all(r5_region in regions for r5_region in R5_regions)
        assert "Other (R5)" not in regions
    finally:
        clean_up_external_repos(nomenclature_config.repositories)
