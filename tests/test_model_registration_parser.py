import yaml
from conftest import TEST_DATA_DIR

from nomenclature.cli import parse_model_registration


def test_parse_model_registration(tmp_path):
    mapping_path = tmp_path / "mappings"
    region_path = tmp_path / "regions"
    mapping_path.mkdir()
    region_path.mkdir()

    parse_model_registration(
        TEST_DATA_DIR
        / "region_processing"
        / "region_aggregation"
        / "excel_model_registration.xlsx",
        region_path,
        mapping_path,
    )

    # Test model mapping
    with open(mapping_path / "Model_1.1.yaml", "r", encoding="utf-8") as file:
        obs_model_mapping = yaml.safe_load(file)
    with open(
        TEST_DATA_DIR
        / "region_processing"
        / "region_aggregation"
        / "excel_mapping_reference.yaml",
        "r",
        encoding="utf-8",
    ) as file:
        exp_model_mapping = yaml.safe_load(file)
    assert obs_model_mapping == exp_model_mapping

    # Test model regions
    with open(region_path / "Model_1.1.yaml", "r", encoding="utf-8") as file:
        obs_model_regions = yaml.safe_load(file)
    exp_model_regions = [
        {
            "Model 1.1": [
                {"Model 1.1|Region 1": {"countries": ["Country 1", "Country 2"]}},
                "Region 2",
                "Model 1.1|Region 3",
            ]
        }
    ]
    assert obs_model_regions == exp_model_regions
