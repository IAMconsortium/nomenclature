from nomenclature.processor.requiredTS import RequiredTSConfig
from conftest import TEST_DATA_DIR


def test_RequiredTSConfig():

    exp = {
        "name": "MAGICC",
        "required_timeseries": [
            {
                "variable": "Emissions|CO2",
                "region": "World",
                "years": [2020, 2025, 2050, 2075, 2100],
                "scenario": None,
                "optional": False,
            },
            {
                "variable": "Emissions|CH4",
                "region": "World",
                "years": [2020, 2025, 2050, 2075, 2100],
                "scenario": None,
                "optional": True,
            },
        ],
    }

    obs = RequiredTSConfig.from_file(TEST_DATA_DIR / "requiredTS" / "requiredTS.yaml")

    assert obs.dict() == exp
