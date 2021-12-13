from pathlib import Path

import jsonschema
import pydantic
import pytest
from nomenclature.processor.region import (
    ModelMappingCollisionError,
    RegionAggregationMapping,
    RegionProcessor,
)

from conftest import TEST_DATA_DIR

TEST_FOLDER_REGION_MAPPING = TEST_DATA_DIR / "region_aggregation"


def test_mapping():
    mapping_file = "working_mapping.yaml"
    # Test that the file is read and represented correctly
    obs = RegionAggregationMapping.from_file(TEST_FOLDER_REGION_MAPPING / mapping_file)
    exp = {
        "model": "model_a",
        "file": (TEST_FOLDER_REGION_MAPPING / mapping_file).relative_to(Path.cwd()),
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
        RegionAggregationMapping.from_file(TEST_FOLDER_REGION_MAPPING / file)


@pytest.mark.parametrize(
    "region_processor_path",
    [
        TEST_DATA_DIR / "regionprocessor_working",
        (TEST_DATA_DIR / "regionprocessor_working").relative_to(Path.cwd()),
    ],
)
def test_region_processor_working(region_processor_path):

    obs = RegionProcessor.from_directory(region_processor_path)
    exp_data = [
        {
            "model": "model_a",
            "file": (
                TEST_DATA_DIR / "regionprocessor_working/mapping_1.yaml"
            ).relative_to(Path.cwd()),
            "native_regions": [
                {"name": "World", "rename": None},
            ],
            "common_regions": None,
        },
        {
            "model": "model_b",
            "file": (
                TEST_DATA_DIR / "regionprocessor_working/mapping_2.yaml"
            ).relative_to(Path.cwd()),
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
        "model_(a|b)\n.*region_a.*mapping_(1|2).yaml.*value_error.region_not_defined."
        "*\n.*model_(a|b)\n.*region_a.*mapping_(1|2).yaml.*value_error."
        "region_not_defined"
    )
    with pytest.raises(pydantic.ValidationError, match=error_msg):
        RegionProcessor.from_directory(
            TEST_DATA_DIR / "regionprocessor_not_defined"
        ).validate_mappings(simple_definition)


def test_region_processor_duplicate_model_mapping():
    error_msg = ".*model_a.*mapping_(1|2).yaml.*mapping_(1|2).yaml"
    with pytest.raises(ModelMappingCollisionError, match=error_msg):
        RegionProcessor.from_directory(TEST_DATA_DIR / "regionprocessor_duplicate")


def test_region_processor_wrong_args():
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
            TEST_DATA_DIR / "regionprocessor_working/mapping_1.yaml"
        )
