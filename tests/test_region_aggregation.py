import jsonschema
import pydantic
import pytest
from pathlib import Path
from nomenclature.region_mapping_models import RegionAggregationMapping

from conftest import TEST_DATA_DIR

test_folder = TEST_DATA_DIR / "region_aggregation"


def test_mapping():
    mapping_file = "working_mapping.yaml"
    # Test that the file is read and represented correctly
    obs = RegionAggregationMapping.create_from_region_mapping(
        test_folder / mapping_file
    )
    exp = {
        "model": "model_a",
        "file": test_folder / mapping_file,
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
        RegionAggregationMapping.create_from_region_mapping(test_folder / file)


def test_model_only_mapping():
    # test that a region mapping runs also with only a model
    exp = {
        "model": "model_a",
        "file": test_folder / "working_mapping_model_only.yaml",
        "native_regions": None,
        "common_regions": None,
    }
    obs = RegionAggregationMapping.create_from_region_mapping(
        test_folder / "working_mapping_model_only.yaml"
    )
    assert exp == obs.dict()
