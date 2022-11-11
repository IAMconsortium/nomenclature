import pytest

from nomenclature.code import VariableCode


def test_variable_without_unit_raises():
    with pytest.raises(ValueError, match="unit\n.*required"):
        VariableCode(name="No unit")


def test_variable_alias_setting():
    assert (
        VariableCode.from_dict(
            {"Var1": {"unit": None, "skip_region_aggregation": True}}
        ).skip_region_aggregation
        is True
    )
    assert (
        VariableCode.from_dict(
            {"Var2": {"unit": None, "skip-region-aggregation": True}}
        ).skip_region_aggregation
        is True
    )
