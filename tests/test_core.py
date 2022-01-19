import copy
import pytest

import pandas as pd
from nomenclature.core import process
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.region import RegionProcessor
from pyam import IAMC_IDX, IamDataFrame, assert_iamframe_equal

from conftest import TEST_DATA_DIR


def test_region_processing_rename():
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
                ["model_a", "scen_a", "region_a", "Primary Energy", "EJ/yr", 1, 2],
                ["model_a", "scen_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
                ["model_a", "scen_a", "region_C", "Primary Energy", "EJ/yr", 5, 6],
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


def test_region_processing_complete():
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
            TEST_DATA_DIR / "region_processing/complete_processing"
        ),
    )
    assert_iamframe_equal(obs, exp)


@pytest.mark.parametrize(
    "folder, exp_df",
    [
        (
            "weighted_aggregation",
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_a", "World", "Emissions|CO2", "Mt CO2", 5, 8],
                ["model_a", "scen_a", "World", "Price|Carbon", "USD/t CO2", 2.8, 7.0],
            ],
        ),
        (
            "weighted_aggregation_rename",
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_a", "World", "Emissions|CO2", "Mt CO2", 5, 8],
                ["model_a", "scen_a", "World", "Price|Carbon", "USD/t CO2", 2.8, 7.0],
                ["model_a", "scen_a", "World", "Price|Carbon (Max)", "USD/t CO2", 3, 8],
            ],
        ),
    ],
)
def test_region_processing_weighted_aggregation(folder, exp_df):
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

    exp = IamDataFrame(pd.DataFrame(exp_df, columns=IAMC_IDX + [2005, 2010]))

    obs = process(
        test_df,
        DataStructureDefinition(TEST_DATA_DIR / "region_processing" / folder / "dsd"),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing" / folder / "aggregate"
        ),
    )
    assert_iamframe_equal(obs, exp)


def test_region_processing_skip_aggregation():
    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 1, 2],
                ["m_a", "s_a", "region_B", "Primary Energy", "EJ/yr", 3, 4],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )
    exp = test_df

    obs = process(
        test_df,
        DataStructureDefinition(
            TEST_DATA_DIR / "region_processing/skip_aggregation/dsd"
        ),
        processor=RegionProcessor.from_directory(
            TEST_DATA_DIR / "region_processing/skip_aggregation/mappings"
        ),
    )
    assert_iamframe_equal(obs, exp)
