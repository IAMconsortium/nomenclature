from typing import Type, ValuesView
import pytest
import yaml
from nomenclature.region_mapping_models import RegionAggregationMapping
from jsonschema.exceptions import ValidationError

from conftest import TEST_DATA_DIR

test_folder = TEST_DATA_DIR / "region_aggregation"


@pytest.mark.skip(reason="Testing only illegal files")
def test_mapping():
    mapping_file = "working_mapping.yml"
    # Test that the file is read and represented correctly
    ram = RegionAggregationMapping.create_from_region_mapping(
        test_folder / mapping_file
    )
    reference = {
        "model": "MESSAGEix-Materials 1.1",
        "native_regions": [
            {"name": "EEU", "rename": "Central and Eastern Europe"},
            {"name": "FSU", "rename": "Former Soviet Union"},
            {"name": "WEU", "rename": None},
        ],
        "common_regions": [
            {
                "name": "Eastern Europe, Caucasus and Central Asia",
                "constituent_regions": [
                    {"name": "EEU", "rename": None},
                    {"name": "FSU", "rename": None},
                ],
            },
            {
                "name": "Europe",
                "constituent_regions": [{"name": "WEU", "rename": None}],
            },
        ],
    }
    assert ram.dict() == reference


@pytest.mark.parametrize(
    "file, error_type, error_msg_pattern",
    [
        (
            "illegal_mapping_1.yml",
            ValidationError,
            ".*'Eastern Europe.*not.*'array'.*",
        ),
        (
            "illegal_mapping_2.yml",
            ValidationError,
            "Additional properties are not allowed.*",
        ),
        (
            "illegal_mapping_3.yml",
            ValueError,
            ".*Overlapping.*Eastern Europe, Caucasus.*",
        ),
        ("illegal_mapping_4.yml", ValueError, ".*Two or more.*Europe.*"),
        ("illegal_mapping_5.yml", ValueError, ".*Two or more.*Europe.*"),
        (
            "illegal_mapping_6.yml",
            ValueError,
            ".*common regions.*Eastern Europe, Caucasus.*",
        ),
    ],
)
def test_illegal_mappings(file, error_type, error_msg_pattern):
    # This is to test a few different failure conditions

    with pytest.raises(error_type, match=error_msg_pattern):
        RegionAggregationMapping.create_from_region_mapping(test_folder / file)


@pytest.mark.skip(reason="Testing only illegal files")
def test_model_only_mapping():
    # test that a region mapping runs also with only a model
    reference = {
        "model": "MESSAGEix-Materials 1.1",
        "native_regions": None,
        "common_regions": None,
    }
    model_only_mapping = RegionAggregationMapping.create_from_region_mapping(
        test_folder / "working_mapping_model_only.yml"
    )
    assert reference == model_only_mapping.dict()
