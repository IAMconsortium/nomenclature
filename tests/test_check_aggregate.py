import pytest
import pandas as pd
from nomenclature.core import process
from nomenclature.definition import DataStructureDefinition
from pyam import IAMC_IDX, IamDataFrame

from conftest import TEST_DATA_DIR

TEST_DF = IamDataFrame(
    pd.DataFrame(
        [
            ["Final Energy", "EJ/yr", 9, 13],
            ["Final Energy|Gas", "EJ/yr", 4, 6],
            ["Final Energy|Electricity", "EJ/yr", 5, 7],
            ["Final Energy|Residential", "EJ/yr", 2, 4],
            ["Final Energy|Industry", "EJ/yr", 7, 9],
            ["Final Energy|Industry|Gas", "EJ/yr", 3, 4],
            ["Final Energy|Industry|Electricity", "EJ/yr", 4, 5],
        ],
        columns=["variable", "unit", 2005, 2010],
    ),
    **dict(model="model_a", scenario="scen_a", region="World"),
)


def test_check_aggregate_single_components():
    """Assert that the aggregate-check passes with a single list of components"""
    dsd = DataStructureDefinition(TEST_DATA_DIR / "check_aggregate" / "components")

    # aggregation check returns None if no inconsistencies are found
    assert dsd.check_aggregate(TEST_DF) is None


def test_check_aggregate_multiple_components():
    """Assert that the aggregate-check passes with multiple components lists"""
    dsd = DataStructureDefinition(TEST_DATA_DIR / "check_aggregate" / "components_dict")

    # aggregation check returns None if no inconsistencies are found
    assert dsd.check_aggregate(TEST_DF) is None
