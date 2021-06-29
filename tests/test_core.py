import pytest
import nomenclature as nc


def test_nonexisting_path_raises():
    """Check that initializing a Nomenclature with a non-existing path raises"""
    with pytest.raises(ValueError, match="Path to definitions does not exist: foo"):
        nc.Nomenclature("foo")