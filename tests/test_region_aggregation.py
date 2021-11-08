import jsonschema
import pydantic
import pytest
from nomenclature.region_mapping_models import (
    RegionAggregationMapping,
    RegionProcessor,
    ModelMappingCollisionError,
)

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
                "constituent_regions": [
                    {"name": "region_a", "rename": None},
                    {"name": "region_b", "rename": None},
                ],
            },
            {
                "name": "common_region_2",
                "constituent_regions": [{"name": "region_c", "rename": None}],
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
    ],
)
def test_illegal_mappings(file, error_type, error_msg_pattern):
    # This is to test a few different failure conditions

    with pytest.raises(error_type, match=f"{error_msg_pattern}{file}.*"):
        RegionAggregationMapping.create_from_region_mapping(
            TEST_FOLDER_REGION_MAPPING / file
        )


def test_model_only_mapping():
    # test that a region mapping runs also with only a model
    exp = {
        "model": "model_a",
        "file": TEST_FOLDER_REGION_MAPPING / "working_mapping_model_only.yaml",
        "native_regions": None,
        "common_regions": None,
    }
    obs = RegionAggregationMapping.create_from_region_mapping(
        TEST_FOLDER_REGION_MAPPING / "working_mapping_model_only.yaml"
    )
    assert exp == obs.dict()


def test_region_processor_working(simple_nomenclature):

    obs = RegionProcessor.from_directory(
        TEST_DATA_DIR / "regionprocessor_working", simple_nomenclature
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
                    "constituent_regions": [
                        {"name": "region_a", "rename": None},
                        {"name": "region_b", "rename": None},
                    ],
                }
            ],
        },
    ]
    exp_models = {value["model"] for value in exp_data}
    exp_dict = {value["model"]: value for value in exp_data}

    assert exp_models == set(obs.mappings.keys())
    assert all(exp_dict[m] == obs.mappings[m].dict() for m in exp_models)


def test_region_processor_not_defined(simple_nomenclature):
    # Test a RegionProcessor with regions that are not defined in the data structure
    # definition
    error_msg = (
        "model_b\n.*region_a.*mapping_2.yaml.*value_error.region_not_defined."
        "*\n.*model_a\n.*region_a.*mapping_1.yaml.*value_error.region_not_defined"
    )
    with pytest.raises(pydantic.ValidationError, match=error_msg):
        RegionProcessor.from_directory(
            TEST_DATA_DIR / "regionprocessor_not_defined", simple_nomenclature
        )


def test_region_processor_duplicate_model_mapping(simple_nomenclature):
    error_msg = ".*model_a.*mapping_1.yaml.*mapping_2.yaml"
    with pytest.raises(ModelMappingCollisionError, match=error_msg):
        RegionProcessor.from_directory(
            TEST_DATA_DIR / "regionprocessor_duplicate", simple_nomenclature
        )


def test_region_processor_wrong_args(simple_nomenclature):
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
            simple_nomenclature,
        )
