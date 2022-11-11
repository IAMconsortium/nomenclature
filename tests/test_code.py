import pytest

from nomenclature.code import VariableCode


def test_variable_without_unit_raises():
    with pytest.raises(ValueError, match="unit\n.*required"):
        VariableCode(name="No unit")
