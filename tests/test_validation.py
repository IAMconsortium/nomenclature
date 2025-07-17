import pytest
import nomenclature
from nomenclature import DataStructureDefinition
from pyam import IamDataFrame

from conftest import TEST_DATA_DIR
import nomenclature.config


MATCH_FAIL_VALIDATION = "The validation failed. Please check the log for details."


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

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        simple_definition.validate(simple_df)
    assert (
        "Please refer to https://files.ece.iiasa.ac.at/data_structure_definition/"
        "data_structure_definition-template.xlsx for the list of allowed variables."
        in caplog.text
    )


def test_validation_fails_unit(simple_definition, simple_df, caplog):
    """Changing a unit raises"""
    simple_df.rename(unit={"EJ/yr": "GWh/yr"}, inplace=True)

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        simple_definition.validate(simple_df)
    assert (
        "Please refer to https://files.ece.iiasa.ac.at/data_structure_definition/"
        "data_structure_definition-template.xlsx for the list of allowed units."
        in caplog.text
    )


def test_validation_fails_region(simple_definition, simple_df, caplog):
    """Changing a region name raises"""
    simple_df.rename(region={"World": "foo"}, inplace=True)

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        simple_definition.validate(simple_df)
    assert (
        "Please refer to https://files.ece.iiasa.ac.at/data_structure_definition/"
        "data_structure_definition-template.xlsx for the list of allowed regions."
        in caplog.text
    )


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
    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        definition.validate(simple_df.rename(scenario={"scen_a": "scen_c"}))

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

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        definition.validate(simple_df.rename(scenario={"scen_a": "foo"}))


@pytest.mark.parametrize(
    "rename_mapping, config, should_pass, error_substring",
    [
        # default config values
        (
            {2005: "2005-06-17 00:00+01:00", 2010: "2010-06-17 00:00+01:00"},
            "datetime_year",
            False,
            "Invalid time domain",
        ),
        # with datetime=True, any timezone is allowed
        (
            {2005: "2005-06-17 00:00+02:00", 2010: "2010-06-17 00:00+02:00"},
            "datetime_true",
            True,
            None,
        ),
        # with datetime=False and timezone, raise
        (
            {2005: "2005-06-17 00:00+02:00", 2010: "2010-06-17 00:00+02:00"},
            "datetime_false",
            False,
            "Timezone is set",
        ),
        # timezone config
        (
            {2005: "2005-06-17 00:00+01:00", 2010: "2010-06-17 00:00+01:00"},
            "datetime_utc",
            True,
            None,
        ),
        (
            {2005: "2005-06-17 00:00+02:00", 2010: "2010-06-17 00:00+02:00"},
            "datetime_utc",
            False,
            "invalid timezone",
        ),
        (
            {2005: "2005-06-17 00:00", 2010: "2010-06-17 00:00"},
            "datetime_utc",
            False,
            "missing timezone",
        ),
    ],
)
def test_validate_time_entry(
    simple_df,
    simple_definition,
    rename_mapping,
    config,
    should_pass,
    error_substring,
    caplog,
):
    """Check datetime validation with different timezone configurations:
    - default config (allow year time domain)
    - datetime=True (allow any timezone)
    - datetime=False (don't allow timezones)
    - timezone=UTC (allow specific timezone)"""
    if error_substring == "Timezone is set":
        with pytest.raises(ValueError, match=error_substring):
            nomenclature.config.NomenclatureConfig.from_file(
                TEST_DATA_DIR / "config" / f"{config}.yaml"
            )
        return
    simple_definition.config = nomenclature.config.NomenclatureConfig.from_file(
        TEST_DATA_DIR / "config" / f"{config}.yaml"
    )
    df = IamDataFrame(
        simple_df.data.rename(columns={"year": "time"}).replace(rename_mapping)
    )
    if should_pass:
        assert simple_definition.validate(df) is None
    else:
        with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
            simple_definition.validate(df)
        assert error_substring in caplog.text
