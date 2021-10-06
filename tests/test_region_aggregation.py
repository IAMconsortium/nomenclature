import pytest
import yaml
from nomenclature.region_mapping_models import (
    RegionAggregationMapping,
    convert_region_mapping,
)

from conftest import TEST_DATA_DIR

test_folder = TEST_DATA_DIR / "region_aggregation"


@pytest.mark.parametrize(
    "mapping_file",
    ["working_message_mapping_cr_dict.yml", "working_message_mapping_cr_list.yml"],
)
def test_mapping(mapping_file):
    # Test that the file is read and represented correctly
    ram = convert_region_mapping(test_folder / mapping_file)
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


def test_model_only():
    # test that a region mapping runs also with only a model
    reference = {
        "model": "MESSAGEix-Materials 1.1",
        "native_regions": None,
        "common_regions": None,
    }
    model_only_mapping = convert_region_mapping(
        test_folder / "working_message_mapping_model_only.yml"
    )
    assert reference == model_only_mapping.dict()
