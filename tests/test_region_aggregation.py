import pytest
import yaml
from nomenclature.region_mapping_models import (
    RegionAggregationMapping,
    convert_region_mapping,
)

from conftest import TEST_DATA_DIR

test_folder = TEST_DATA_DIR / "region_aggregation"


def test_properly_formatted_mapping():
    # test that the properly formatted file is read and represented correctly
    file = test_folder / "message_mapping_verbose.yml"
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


@pytest.mark.parametrize(
    "mapping_file",
    ["working_message_mapping_cr_dict.yml", "working_message_mapping_cr_list.yml"],
)
def test_current_format(mapping_file):
    # test that the file formatted according to current spec
    properly_formatted_file = test_folder / "message_mapping_verbose.yml"
    with open(properly_formatted_file, "r") as f:
        mapping = yaml.load(f)
    ram_verbose = RegionAggregationMapping(**mapping)
    ram_current = convert_region_mapping(test_folder / mapping_file)
    assert ram_current == ram_verbose
