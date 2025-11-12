import pytest
from conftest import TEST_DATA_DIR
from pyam import IamDataFrame

from nomenclature import DataStructureDefinition
from nomenclature.config import NomenclatureConfig
from nomenclature.exceptions import (
    NomenclatureValidationError,
    TimeDomainError,
    UnknownRegionError,
    UnknownScenarioError,
    UnknownVariableError,
    WrongUnitError,
)

MATCH_FAIL_VALIDATION = "Validation failed, details"


def test_validation(simple_definition, simple_df):
    """A simple validation passes as expected"""
    simple_definition.validate(simple_df)


def test_validation_dimensionless_unit(simple_definition, simple_df):
    """Assert validating against a dimensionless quantity"""
    mapping = dict(variable={"Primary Energy|Coal": "Share|Coal"}, unit={"EJ/yr": ""})
    simple_df.rename(mapping, inplace=True)

    simple_definition.validate(simple_df)


def test_validation_brackets(extras_definition, simple_df):
    """Assert validating against a variable with special characters"""
    mapping = dict(variable={"Primary Energy|Coal": "Variable (w/ bunkers)"})
    simple_df.rename(mapping, inplace=True)

    extras_definition.validate(simple_df)


def test_validation_fails_variable(simple_definition, simple_df, caplog):
    """Changing a variable name raises"""
    simple_df.rename(variable={"Primary Energy": "foo"}, inplace=True)

    with pytest.raises(
        NomenclatureValidationError, match=MATCH_FAIL_VALIDATION
    ) as excinfo:
        simple_definition.validate(simple_df)
    assert excinfo.group_contains(
        UnknownVariableError,
        match=(
            r"foo\n\n"
            r"Please refer to https://files.ece.iiasa.ac.at/data_structure_definition/"
            r"data_structure_definition-template.xlsx for the list of allowed "
            r"variables."
        ),
    )


def test_validation_fails_unit(simple_definition, simple_df, caplog):
    """Changing a unit raises"""
    simple_df.rename(unit={"EJ/yr": "GWh/yr"}, inplace=True)

    with pytest.raises(
        NomenclatureValidationError, match=MATCH_FAIL_VALIDATION
    ) as excinfo:
        simple_definition.validate(simple_df)
    assert excinfo.group_contains(
        WrongUnitError,
        match=r"- 'Primary Energy' - expected: 'EJ/yr', found: 'GWh/yr'",
    )


def test_validation_fails_region(simple_definition, simple_df, caplog):
    """Changing a region name raises"""
    simple_df.rename(region={"World": "foo"}, inplace=True)

    with pytest.raises(
        NomenclatureValidationError, match=MATCH_FAIL_VALIDATION
    ) as excinfo:
        simple_definition.validate(simple_df)
    assert excinfo.group_contains(UnknownRegionError, match=r"foo")


def test_validation_multiple_units(extras_definition, simple_df):
    """Validating against a VariableCode with multiple units works as expected"""
    extras_definition.validate(
        simple_df.filter(variable="Primary Energy|Coal").rename(
            unit={"EJ/yr": "GWh/yr"}
        )
    )


def test_validation_with_custom_dimension(simple_df):
    """Check validation with a custom DataStructureDefinition dimension"""

    definition = DataStructureDefinition(
        TEST_DATA_DIR / "data_structure_definition" / "custom_dimension_nc",
        dimensions=["region", "variable", "scenario"],
    )

    # validating against all dimensions fails ("scen_c" not in ["scen_a", "scenario_b"])
    with pytest.raises(
        NomenclatureValidationError, match=MATCH_FAIL_VALIDATION
    ) as excinfo:
        definition.validate(simple_df.rename(scenario={"scen_a": "scen_c"}))

    assert excinfo.group_contains(UnknownScenarioError, match=r"scen_c")

    # validating against specific dimensions works (in spite of conflict in "scenario")
    definition.validate(
        simple_df.rename(scenario={"scen_a": "scen_c"}),
        dimensions=["region", "variable"],
    )

    # validating against all dimensions works
    definition.validate(simple_df)


def test_wildcard_match(simple_df):
    definition = DataStructureDefinition(
        TEST_DATA_DIR / "codelist" / "wildcard",
        dimensions=["scenario"],
    )

    assert definition.validate(simple_df) is None

    with pytest.raises(
        NomenclatureValidationError, match=MATCH_FAIL_VALIDATION
    ) as excinfo:
        definition.validate(simple_df.rename(scenario={"scen_a": "foo"}))
    assert excinfo.group_contains(UnknownScenarioError, match=r"foo")


@pytest.mark.parametrize(
    "rename_mapping, config_file_name",
    [
        # with datetime=True, any timezone is allowed
        (
            {2005: "2005-06-17 00:00+02:00", 2010: "2010-06-17 00:00+02:00"},
            "datetime_true",
        ),
        # timezone config
        (
            {2005: "2005-06-17 00:00+01:00", 2010: "2010-06-17 00:00+01:00"},
            "datetime_utc",
        ),
    ],
)
def test_validate_time_entry(
    simple_df,
    simple_definition,
    rename_mapping,
    config_file_name,
):
    """Test two different datetime values pass the validation"""

    simple_definition.config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "config" / f"{config_file_name}.yaml"
    )
    df = IamDataFrame(
        simple_df.data.rename(columns={"year": "time"}).replace(rename_mapping)
    )

    assert simple_definition.validate(df) is None


@pytest.mark.parametrize(
    "rename_mapping, config_file_name, match",
    [
        # default config values
        (
            {2005: "2005-06-17 00:00+01:00", 2010: "2010-06-17 00:00+01:00"},
            "datetime_year",
            "Invalid time domain",
        ),
        (
            {2005: "2005-06-17 00:00+02:00", 2010: "2010-06-17 00:00+02:00"},
            "datetime_utc",
            "invalid timezone",
        ),
        (
            {2005: "2005-06-17 00:00", 2010: "2010-06-17 00:00"},
            "datetime_utc",
            "missing timezone",
        ),
    ],
)
def test_validate_time_entry_raises(
    simple_df,
    simple_definition,
    rename_mapping,
    config_file_name,
    match,
):
    """Test three different time validation error cases"""
    simple_definition.config = NomenclatureConfig.from_file(
        TEST_DATA_DIR / "config" / f"{config_file_name}.yaml"
    )
    df = IamDataFrame(
        simple_df.data.rename(columns={"year": "time"}).replace(rename_mapping)
    )

    with pytest.raises(
        NomenclatureValidationError, match=MATCH_FAIL_VALIDATION
    ) as excinfo:
        simple_definition.validate(df)
    assert excinfo.group_contains(TimeDomainError, match=match)
