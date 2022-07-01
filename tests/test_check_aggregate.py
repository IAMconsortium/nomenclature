import pytest
import pandas as pd
import pandas.testing as pdt
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

# create a copy where aggregation tests will fail
FAILING_DF = TEST_DF.copy()
FAILING_DF._data.iloc[6] = 8


def expected_fail_return(name):
    index = pd.Index(
        [
            ("model_a", "scen_a", "World", f"Final Energy{name}", "EJ/yr", 2005),
            ("model_a", "scen_a", "World", "Final Energy|Industry", "EJ/yr", 2005),
        ],
        names=["model", "scenario", "region", "variable", "unit", "year"],
    )
    columns = ["variable", "components"]
    return pd.DataFrame([[9, 10], [8, 7]], columns=columns, index=index)


@pytest.mark.parametrize("components", ["components", "components_dict"])
def test_check_aggregate_passing(components):
    """Assert that the aggregate-check passes with different types of components"""

    dsd = DataStructureDefinition(TEST_DATA_DIR / "check_aggregate" / components)

    # aggregation check returns None if no inconsistencies are found
    assert dsd.check_aggregate(TEST_DF) is None


@pytest.mark.parametrize(
    "components, exp",
    [
        ("components", expected_fail_return("")),
        ("components_dict", expected_fail_return(" [By sector]")),
    ],
)
def test_check_aggregate_failing(components, exp):
    """Assert that the aggregate-check fails with different types of components"""

    dsd = DataStructureDefinition(TEST_DATA_DIR / "check_aggregate" / components)
    pdt.assert_frame_equal(dsd.check_aggregate(FAILING_DF), exp)
