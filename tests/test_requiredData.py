from nomenclature.processor.requiredData import RequiredDataConfig
from conftest import TEST_DATA_DIR


def test_RequiredDataConfig():

    exp = {
        "name": "MAGICC",
        "required_timeseries": [
            {
                "variable": "Emissions|CO2",
                "region": "World",
                "years": [2020, 2030, 2040, 2050],
                "optional": False,
            },
            {
                "variable": "Emissions|CH4",
                "region": "World",
                "years": [2020, 2025, 2050, 2075, 2100],
                "optional": True,
            },
        ],
    }

    obs = RequiredDataConfig.from_file(
        TEST_DATA_DIR / "requiredData" / "requiredData.yaml"
    )

    assert obs.dict() == exp
