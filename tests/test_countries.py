import pytest

from nomenclature import countries


@pytest.mark.parametrize(
    "nc_name, iso_name, alpha_3",
    [("Bolivia", "Bolivia, Plurinational State of", "BOL")],
)
def test_countries_override(nc_name, iso_name, alpha_3):
    """Check that countries renamed from ISO 3166 can be found in both directions"""

    assert countries.get(name=nc_name).alpha_3 == "BOL"
    assert countries.get(name=iso_name).alpha_3 == "BOL"
    assert countries.get(alpha_3=alpha_3).name == nc_name


def test_countries_add():
    """Check that countries added to ISO 3166 can be found"""

    assert countries.get(name="Kosovo").name == "Kosovo"
    with pytest.raises(AttributeError):
        countries.get(name="Kosovo").alpha_3


@pytest.mark.parametrize("alpha_2_eu, alpha_2", [("EL", "GR"), ("UK", "GB")])
def test_alternative_alpha2(alpha_2_eu, alpha_2):
    """Check that the handling of alternative alpha-2 codes works"""
    assert countries.get(alpha_2=alpha_2_eu).alpha_2 == alpha_2
