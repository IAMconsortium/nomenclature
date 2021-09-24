from nomenclature.region_mapping_models import (
    RegionAggregationMapping,
    convert_region_mapping,
)
from conftest import TEST_DATA_DIR
import pytest
import yaml
from nomenclature import DataStructureDefinition

test_folder = TEST_DATA_DIR / "region_aggregation"


def test_properly_formatted_mapping():
    # test that the properly formatted file is read and represented correctly
    file = test_folder / "message_mapping_proper.yml"
    with open(file, "r") as f:
        mapping = yaml.load(f)
    ram = RegionAggregationMapping(**mapping)
    reference = {
        "model": "MESSAGEix-Materials 1.1",
        "native_regions": [
            {"name": "AFR", "rename": "Africa"},
            {"name": "WEU", "rename": None},
        ],
        "common_regions": [
            {
                "name": "Africa",
                "constituent_regions": [{"name": "AFR", "rename": None}],
            },
            {
                "name": "Europe",
                "constituent_regions": [{"name": "WEU", "rename": None}],
            },
        ],
    }
    assert ram.dict() == reference


def test_current_format():
    # test that the file formatted according to current spec
    properly_formatted_file = test_folder / "message_mapping_proper.yml"
    with open(properly_formatted_file, "r") as f:
        mapping = yaml.load(f)
    current_spec_file = test_folder / "message_mapping.yml"
    ram_proper = RegionAggregationMapping(**mapping)
    ram_current = convert_region_mapping(current_spec_file)
    assert ram_current == ram_proper
