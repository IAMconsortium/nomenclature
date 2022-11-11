import pytest

from nomenclature.code import Code, VariableCode


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


def test_illegal_additional_attribute():
    match = "i'm not allowed.*'code1'.*not allowed"
    with pytest.raises(ValueError, match=match):
        Code(name="code1", attributes={"i'm not allowed": True})
