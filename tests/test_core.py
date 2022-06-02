import copy
import pytest

import numpy as np
import pandas as pd
from nomenclature.core import process
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.region import RegionProcessor
from pyam import IAMC_IDX, IamDataFrame, assert_iamframe_equal

from conftest import TEST_DATA_DIR


@pytest.mark.parametrize("model_name", ["model_a", "model_c"])
def test_region_processing_rename(model_name):
    # Test **only** the renaming aspect, i.e. 3 things:
    # 1. All native regions **with** a renaming property should be renamed correctly
    # 2. All native regions **without** a renaming property should be passed through
    # 3. All regions which are explicitly named should be dropped
    # Testing strategy:
    # 1. Rename region_a -> region_A
    # 2. Leave region_B untouched
    # 3. Drop region_C

    test_df = IamDataFrame(
        pd.DataFrame(
            [
                [model_name, "scen_a", "region_a", "Primary Energy", "EJ/yr", 1, 2],
                [model_name, "scen_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                [model_name, "scen_a", "region_C", "Primary Energy", "EJ/yr", 5, 6],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    exp = copy.deepcopy(test_df)
    exp.filter(region=["region_a", "region_B"], inplace=True)
    exp.rename(region={"region_a": "region_A"}, inplace=True)

    obs = process(
        test_df,
        DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing/rename_only"
        ),
    )

    assert_iamframe_equal(obs, exp)


@pytest.mark.parametrize(
    "rp_dir", ["region_processing/rename_only", "region_processing/empty_aggregation"]
)
def test_region_processing_empty_raises(rp_dir):
    # Test that an empty result of the region-processing raises
    # see also https://github.com/IAMconsortium/pyam/issues/631

    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "region_foo", "Primary Energy", "EJ/yr", 1, 2],
                ["model_b", "scen_a", "region_foo", "Primary Energy", "EJ/yr", 1, 2],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )
    with pytest.raises(ValueError, match=("'model_a', 'model_b'.*empty dataset")):
        process(
            test_df,
            DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd"),
            processor=RegionProcessor.from_directory(TEST_DATA_DIR / rp_dir),
        )


def test_region_processing_no_mapping(simple_df):
    # Test that a model without a mapping is passed untouched

    exp = copy.deepcopy(simple_df)

    obs = process(
        simple_df,
        DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing/no_mapping"
        ),
    )
    assert_iamframe_equal(obs, exp)


def test_region_processing_aggregate():
    # Test only the aggregation feature
    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["model_a", "scen_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["model_a", "scen_a", "region_C", "Primary Energy", "EJ/yr", 5, 6],
                ["model_a", "scen_b", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["model_a", "scen_b", "region_B", "Primary Energy", "EJ/yr", 3, 4],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )
    exp = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_b", "World", "Primary Energy", "EJ/yr", 4, 6],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    obs = process(
        test_df,
        DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing/aggregate_only"
        ),
    )

    assert_iamframe_equal(obs, exp)


@pytest.mark.parametrize(
    "directory", ("complete_processing", "complete_processing_list")
)
def test_region_processing_complete(directory):
    # Test all three aspects of region processing together:
    # 1. Renaming
    # 2. Passing models without a mapping
    # 3. Aggregating correctly

    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "region_a", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["m_a", "s_a", "region_C", "Primary Energy", "EJ/yr", 5, 6],
                ["m_a", "s_a", "region_a", "Primary Energy|Coal", "EJ/yr", 0.5, 1],
                ["m_a", "s_a", "region_B", "Primary Energy|Coal", "EJ/yr", 1.5, 2],
                ["m_b", "s_b", "region_A", "Primary Energy", "EJ/yr", 1, 2],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )
    exp = IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["m_a", "s_a", "region_A", "Primary Energy|Coal", "EJ/yr", 0.5, 1],
                ["m_a", "s_a", "region_B", "Primary Energy|Coal", "EJ/yr", 1.5, 2],
                ["m_a", "s_a", "World", "Primary Energy|Coal", "EJ/yr", 2, 3],
                ["m_b", "s_b", "region_A", "Primary Energy", "EJ/yr", 1, 2],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    obs = process(
        test_df,
        DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing" / directory
        ),
    )
    assert_iamframe_equal(obs, exp)


@pytest.mark.parametrize(
    "folder, exp_df, args",
    [
        (
            "weighted_aggregation",
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_a", "World", "Emissions|CO2", "Mt CO2", 5, 8],
                ["model_a", "scen_a", "World", "Price|Carbon", "USD/t CO2", 2.8, 7.0],
            ],
            None,
        ),
        (
            "weighted_aggregation_rename",
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_a", "World", "Emissions|CO2", "Mt CO2", 5, 8],
                ["model_a", "scen_a", "World", "Price|Carbon", "USD/t CO2", 2.8, 7.0],
                ["model_a", "scen_a", "World", "Price|Carbon (Max)", "USD/t CO2", 3, 8],
            ],
            None,
        ),
        # check that region-aggregation with missing weights passes (inconsistent index)
        # TODO check the log output
        (
            "weighted_aggregation",
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_a", "World", "Emissions|CO2", "Mt CO2", 5, np.nan],
            ],
            dict(variable="Emissions|CO2", year=2010, keep=False),
        ),
    ],
)
def test_region_processing_weighted_aggregation(folder, exp_df, args, caplog):
    # test a weighed sum

    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["model_a", "scen_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["model_a", "scen_a", "region_A", "Emissions|CO2", "Mt CO2", 4, 6],
                ["model_a", "scen_a", "region_B", "Emissions|CO2", "Mt CO2", 1, 2],
                ["model_a", "scen_a", "region_A", "Price|Carbon", "USD/t CO2", 3, 8],
                ["model_a", "scen_a", "region_B", "Price|Carbon", "USD/t CO2", 2, 4],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    if args is not None:
        test_df = test_df.filter(**args)

    exp = IamDataFrame(pd.DataFrame(exp_df, columns=IAMC_IDX + [2005, 2010]))

    obs = process(
        test_df,
        DataStructureDefinition(TEST_DATA_DIR / "region_processing" / folder / "dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing" / folder / "aggregate"
        ),
    )
    assert_iamframe_equal(obs, exp)
    # check the logs since the presence of args should cause a warning in the logs
    if args:
        logmsg = (
            "Could not aggregate 'Price|Carbon' for region 'World' "
            "({'weight': 'Emissions|CO2'})"
        )
        assert logmsg in caplog.text


@pytest.mark.parametrize(
    "model_name, region_names",
    [("model_a", ("region_A", "region_B")), ("model_b", ("region_A", "region_b"))],
)
def test_region_processing_skip_aggregation(model_name, region_names):
    # Testing two cases:
    # * model "m_a" renames native regions and the world region is skipped
    # * model "m_b" renames single constituent common regions

    input_df = IamDataFrame(
        pd.DataFrame(
            [
                [model_name, "s_a", region_names[0], "Primary Energy", "EJ/yr", 1, 2],
                [model_name, "s_a", region_names[1], "Primary Energy", "EJ/yr", 3, 4],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )
    exp = IamDataFrame(
        pd.DataFrame(
            [
                [model_name, "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                [model_name, "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    obs = process(
        input_df,
        DataStructureDefinition(
            TEST_DATA_DIR / "region_processing/skip_aggregation/dsd"
        ),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing/skip_aggregation/mappings"
        ),
    )
    assert_iamframe_equal(obs, exp)


@pytest.mark.parametrize(
    "input_data, exp_data, warning",
    [
        (  # Variable is available in provided and aggregated data and the same
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6],
            ],
            [["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6]],
            None,
        ),
        (  # Variable is only available in the provided data
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
            ],
            [["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6]],
            None,
        ),
        (  # Variable is only available in the aggregated data
            [["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6]],
            [["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6]],
            None,
        ),
        (  # Variable is not available in all scenarios in the provided data
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["m_a", "s_b", "region_A", "Primary Energy", "EJ/yr", 5, 6],
                ["m_a", "s_b", "region_B", "Primary Energy", "EJ/yr", 7, 8],
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6],
            ],
            [
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["m_a", "s_b", "World", "Primary Energy", "EJ/yr", 12, 14],
            ],
            None,
        ),
        (  # Using skip-aggregation: true should only take provided results
            [
                ["m_a", "s_a", "region_A", "Skip-Aggregation", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Skip-Aggregation", "EJ/yr", 3, 4],
                ["m_a", "s_a", "World", "Skip-Aggregation", "EJ/yr", 10, 11],
            ],
            [["m_a", "s_a", "World", "Skip-Aggregation", "EJ/yr", 10, 11]],
            None,
        ),
        (  # Using the region-aggregation attribute to create an additional variable
            [
                ["m_a", "s_a", "region_A", "Variable A", "EJ/yr", 1, 10],
                ["m_a", "s_a", "region_B", "Variable A", "EJ/yr", 10, 1],
                ["m_a", "s_a", "World", "Variable A", "EJ/yr", 11, 11],
            ],
            [
                ["m_a", "s_a", "World", "Variable A", "EJ/yr", 11, 11],
                ["m_a", "s_a", "World", "Variable A (max)", "EJ/yr", 10, 10],
            ],
            None,
        ),
        (  # Variable is available in provided and aggregated data but different
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 5, 6],
            ],
            [["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 5, 6]],
            [
                "Difference between original and aggregated data:",
                "m_a   s_a      World  Primary Energy",
                "2005              5            4",
            ],
        ),
        (  # Conflict between overlapping renamed variable and provided data
            [
                ["m_a", "s_a", "region_A", "Variable B", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Variable B", "EJ/yr", 3, 4],
                ["m_a", "s_a", "World", "Variable B", "EJ/yr", 4, 6],
            ],
            [["m_a", "s_a", "World", "Variable B", "EJ/yr", 4, 6]],
            [
                "Difference between original and aggregated data:",
                "m_a   s_a      World  Variable B EJ/yr",
                "2005              4            3",
            ],
        ),
    ],
)
def test_partial_aggregation(input_data, exp_data, warning, caplog):
    # Dedicated test for partial aggregation
    # Test cases are:
    # * Variable is available in provided and aggregated data and the same
    # * Variable is only available in the provided data
    # * Variable is only available in the aggregated data
    # * Variable is not available in all scenarios in the provided data
    # * Using skip-aggregation: true should only take provided results
    # * Using the region-aggregation attribute to create an additional variable
    # * Variable is available in provided and aggregated data but different

    obs = process(
        IamDataFrame(pd.DataFrame(input_data, columns=IAMC_IDX + [2005, 2010])),
        DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing/partial_aggregation"
        ),
    )
    exp = IamDataFrame(pd.DataFrame(exp_data, columns=IAMC_IDX + [2005, 2010]))

    # Assert that we get the expected values
    assert_iamframe_equal(obs, exp)

    # Assert that we get the correct warnings
    if warning is None:
        assert "WARNING" not in caplog.text
    else:
        assert all(c in caplog.text for c in warning)
