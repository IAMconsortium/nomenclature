import copy
import jsonschema
import pydantic
import pytest
import pandas as pd
from nomenclature.core import DataStructureDefinition
from nomenclature.region_mapping_models import (
    RegionAggregationMapping,
    RegionProcessor,
    ModelMappingCollisionError,
)
from pyam import IAMC_IDX, assert_iamframe_equal, IamDataFrame
from conftest import TEST_DATA_DIR

TEST_FOLDER_REGION_MAPPING = TEST_DATA_DIR / "region_aggregation"


def test_mapping():
    mapping_file = "working_mapping.yaml"
    # Test that the file is read and represented correctly
    obs = RegionAggregationMapping.create_from_region_mapping(
        TEST_FOLDER_REGION_MAPPING / mapping_file
    )
    exp = {
        "model": "model_a",
        "file": TEST_FOLDER_REGION_MAPPING / mapping_file,
        "native_regions": [
            {"name": "region_a", "rename": "alternative_name_a"},
            {"name": "region_b", "rename": "alternative_name_b"},
            {"name": "region_c", "rename": None},
        ],
        "common_regions": [
            {
                "name": "common_region_1",
                "constituent_regions": ["region_a", "region_b"],
            },
            {
                "name": "common_region_2",
                "constituent_regions": ["region_c"],
            },
        ],
    }
    assert obs.dict() == exp


@pytest.mark.parametrize(
    "file, error_type, error_msg_pattern",
    [
        (
            "illegal_mapping_invalid_format_dict.yaml",
            jsonschema.ValidationError,
            ".*common_region_1.*not.*'array'.*",
        ),
        (
            "illegal_mapping_illegal_attribute.yaml",
            jsonschema.ValidationError,
            "Additional properties are not allowed.*",
        ),
        (
            "illegal_mapping_conflict_regions.yaml",
            pydantic.ValidationError,
            ".*Name collision in native and common regions.*common_region_1.*",
        ),
        (
            "illegal_mapping_duplicate_native.yaml",
            pydantic.ValidationError,
            ".*Name collision in native regions.*alternative_name_a.*",
        ),
        (
            "illegal_mapping_duplicate_native_rename.yaml",
            pydantic.ValidationError,
            ".*Name collision in native regions.*alternative_name_a.*",
        ),
        (
            "illegal_mapping_duplicate_common.yaml",
            pydantic.ValidationError,
            ".*Name collision in common regions.*common_region_1.*",
        ),
        (
            "illegal_mapping_model_only.yaml",
            pydantic.ValidationError,
            ".*one of the two: 'native_regions', 'common_regions'.*",
        ),
    ],
)
def test_illegal_mappings(file, error_type, error_msg_pattern):
    # This is to test a few different failure conditions

    with pytest.raises(error_type, match=f"{error_msg_pattern}{file}.*"):
        RegionAggregationMapping.create_from_region_mapping(
            TEST_FOLDER_REGION_MAPPING / file
        )


def test_region_processor_working(simple_definition):

    obs = RegionProcessor.from_directory(
        TEST_DATA_DIR / "regionprocessor_working", simple_definition
    )
    exp_data = [
        {
            "model": "model_a",
            "file": TEST_DATA_DIR / "regionprocessor_working/mapping_1.yaml",
            "native_regions": [
                {"name": "World", "rename": None},
            ],
            "common_regions": None,
        },
        {
            "model": "model_b",
            "file": TEST_DATA_DIR / "regionprocessor_working/mapping_2.yaml",
            "native_regions": None,
            "common_regions": [
                {
                    "name": "World",
                    "constituent_regions": ["region_a", "region_b"],
                }
            ],
        },
    ]
    exp_models = {value["model"] for value in exp_data}
    exp_dict = {value["model"]: value for value in exp_data}

    assert exp_models == set(obs.mappings.keys())
    assert all(exp_dict[m] == obs.mappings[m].dict() for m in exp_models)


def test_region_processor_not_defined(simple_definition):
    # Test a RegionProcessor with regions that are not defined in the data structure
    # definition
    error_msg = (
        "model_b\n.*region_a.*mapping_2.yaml.*value_error.region_not_defined."
        "*\n.*model_a\n.*region_a.*mapping_1.yaml.*value_error.region_not_defined"
    )
    with pytest.raises(pydantic.ValidationError, match=error_msg):
        RegionProcessor.from_directory(
            TEST_DATA_DIR / "regionprocessor_not_defined", simple_definition
        )


def test_region_processor_duplicate_model_mapping(simple_definition):
    error_msg = ".*model_a.*mapping_1.yaml.*mapping_2.yaml"
    with pytest.raises(ModelMappingCollisionError, match=error_msg):
        RegionProcessor.from_directory(
            TEST_DATA_DIR / "regionprocessor_duplicate", simple_definition
        )


def test_region_processor_wrong_args(simple_definition):
    # Test if pydantic correctly type checks the input of RegionProcessor.from_directory

    # Test with an integer
    with pytest.raises(pydantic.ValidationError, match=".*path\n.*not a valid path.*"):
        RegionProcessor.from_directory(123)

    # Test with a file, a path pointing to a directory is required
    with pytest.raises(
        pydantic.ValidationError,
        match=".*path\n.*does not point to a directory.*",
    ):
        RegionProcessor.from_directory(
            TEST_DATA_DIR / "regionprocessor_working/mapping_1.yaml",
            simple_definition,
        )


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

    dsd = DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd")
    rp = RegionProcessor.from_directory(
        TEST_DATA_DIR / "region_processing/rename_only", dsd
    )
    obs = rp.apply(test_df)

    assert_iamframe_equal(obs, exp)


def test_region_processing_no_mapping(simple_df):
    # Test that a model without a mapping is passed untouched

    exp = copy.deepcopy(simple_df)
    dsd = DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd")
    rp = RegionProcessor.from_directory(
        TEST_DATA_DIR / "region_processing/no_mapping", dsd
    )
    obs = rp.apply(simple_df)
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

    dsd = DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd")
    rp = RegionProcessor.from_directory(
        TEST_DATA_DIR / "region_processing/aggregate_only", dsd
    )
    obs = rp.apply(test_df)
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
                ["m_b", "s_b", "region_a", "Primary Energy", "EJ/yr", 1, 2],
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
                ["m_b", "s_b", "region_a", "Primary Energy", "EJ/yr", 1, 2],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    dsd = DataStructureDefinition(TEST_DATA_DIR / "region_processing/dsd")
    rp = RegionProcessor.from_directory(
        TEST_DATA_DIR / "region_processing/complete_processing", dsd
    )
    obs = rp.apply(test_df)
    assert_iamframe_equal(obs, exp)


def test_region_processing_weighted_aggregation():
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

    exp = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 4, 6],
                ["model_a", "scen_a", "World", "Emissions|CO2", "Mt CO2", 5, 8],
                ["model_a", "scen_a", "World", "Price|Carbon", "USD/t CO2", 2.8, 7.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "region_processing/weighted_aggregation/dsd"
    )
    rp = RegionProcessor.from_directory(
        TEST_DATA_DIR / "region_processing/weighted_aggregation/aggregate", dsd
    )
    obs = rp.apply(test_df)
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
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "region_processing/skip_aggregation/dsd"
    )
    rp = RegionProcessor.from_directory(
        TEST_DATA_DIR / "region_processing/skip_aggregation/mappings", dsd
    )
    obs = rp.apply(test_df)
    assert_iamframe_equal(obs, exp)
