import pytest

MATCH_FAIL_VALIDATION = "The validation failed. Please check the log for details."


def test_validation(simple_nomenclature, simple_df):
    """A simple validation passes as expected"""
    simple_nomenclature.validate(simple_df)


def test_validation_dimensionless_unit(simple_nomenclature, simple_df):
    """Assert that validating against a dimensionless quantity"""
    mapping = dict(variable={"Primary Energy|Coal": "Share|Coal"}, unit={"EJ/yr": ""})
    simple_df.rename(mapping, inplace=True)

    simple_nomenclature.validate(simple_df)


def test_validation_fails_variable(simple_nomenclature, simple_df):
    """Changing a variable name raises"""
    simple_df.rename(variable={"Primary Energy": "foo"}, inplace=True)

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        simple_nomenclature.validate(simple_df)


def test_validation_fails_unit(simple_nomenclature, simple_df):
    """Changing a unit raises"""
    simple_df.rename(unit={"EJ/yr": "GWh/yr"}, inplace=True)

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        simple_nomenclature.validate(simple_df)


def test_validation_fails_region(simple_nomenclature, simple_df):
    """Changing a region name raises"""
    simple_df.rename(region={"World": "foo"}, inplace=True)

    with pytest.raises(ValueError, match=MATCH_FAIL_VALIDATION):
        simple_nomenclature.validate(simple_df)
