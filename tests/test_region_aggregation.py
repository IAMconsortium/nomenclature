import pytest
import yaml
from nomenclature.region_mapping_models import RegionAggregationMapping

from conftest import TEST_DATA_DIR

test_folder = TEST_DATA_DIR / "region_aggregation"


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


@pytest.mark.skip(reason="No illegal files yet")
@pytest.mark.parametrize("illegal_mapping", [""])
def test_illegal_mappings(illegal_mapping):
    # This is to test a few mappings that are illegal and should be found as such
    assert False


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
