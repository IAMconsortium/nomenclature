import pytest
import pandas as pd
import pandas.testing as pdt
import numpy as np
from nomenclature.core import process
from nomenclature.definition import DataStructureDefinition
from pyam import IamDataFrame

from conftest import TEST_DATA_DIR

TEST_DF = IamDataFrame(
    pd.DataFrame(
        [
            ["Final Energy", "EJ/yr", 9, np.nan],
            ["Final Energy|Gas", "EJ/yr", 4, 6],
            ["Final Energy|Electricity", "EJ/yr", 5, 7],
            ["Final Energy|Residential", "EJ/yr", 2, 4],
            ["Final Energy|Industry", "EJ/yr", 7, 9],
            ["Final Energy|Industry|Gas", "EJ/yr", 3, np.nan],
            ["Final Energy|Industry|Electricity", "EJ/yr", 4, np.nan],
        ],
        columns=["variable", "unit", 2005, 2010],
    ),
    **dict(model="model_a", scenario="scen_a", region="World"),
)


def expected_fail_return(name):
    index = pd.Index(
        [
            ("model_a", "scen_a", "World", f"Final Energy{name}", "EJ/yr", 2005),
            ("model_a", "scen_a", "World", "Final Energy|Industry", "EJ/yr", 2005),
        ],
        name=("model", "scenario", "region", "variable", "unit", "year"),
    )
    columns = ["variable", "components"]
    return pd.DataFrame([[9.0, 10.0], [8.0, 7.0]], columns=columns, index=index)


@pytest.mark.parametrize(
    "components, components_type",
    [
        ("components", list),
        ("components_dict", dict),
    ],
)
def test_check_aggregate_passing(components, components_type):
    """Assert that the aggregate-check passes with different types of components"""

    dsd = DataStructureDefinition(TEST_DATA_DIR / "check_aggregate" / components)

    # check that components is returned as a basic type (not a codelist)
    assert isinstance(dsd.variable.mapping["Final Energy"].components, components_type)

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

    # create a copy where aggregation tests will fail
    df = TEST_DF.copy()
    df._data.iloc[5] = 8

    # `check_aggregate` returns a dataframe of the inconsistent data
    pdt.assert_frame_equal(dsd.check_aggregate(df), exp)

    # process raises an error (and writes to log, not tested explicitly)
    with pytest.raises(ValueError, match="The validation failed. Please "):
        process(df, dsd)
