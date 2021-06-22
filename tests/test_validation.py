import pytest


def test_validation(simple_nomenclature, simple_df):
    """A simple validation passes as expected"""
    simple_nomenclature.validate(simple_df)


def test_validation_fails_variable(simple_nomenclature, simple_df):
    """A simple validation passes as expected"""
    simple_df.rename(variable={"Primary Energy": "foo"}, inplace=True)

    match = "The validation failed. Please check the log for details."
    with pytest.raises(ValueError, match=match):
        simple_nomenclature.validate(simple_df)


def test_validation_fails_unit(simple_nomenclature, simple_df):
    """A simple validation passes as expected"""
    simple_df.rename(unit={"EJ/yr": "GWh/yr"}, inplace=True)

    match = "The validation failed. Please check the log for details."
    with pytest.raises(ValueError, match=match):
        simple_nomenclature.validate(simple_df)