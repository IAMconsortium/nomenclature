from conftest import TEST_DATA_DIR

from nomenclature import DataStructureDefinition
from nomenclature.processor.data_validator import DataValidator

DATA_VALIDATION_TEST_DIR = TEST_DATA_DIR / "validation" / "validate_data"


def test_DataValidator_from_file():
    exp = DataValidator(
        **{
            "criteria_items": [
                {
                    "region": ["World"],
                    "variable": "Final Energy",
                    "year": [2010],
                    "upper_bound": 2.5,
                    "lower_bound": 1.0,  # test that integer in yaml is cast to float
                }
            ],
            "file": DATA_VALIDATION_TEST_DIR / "simple_validation.yaml",
        }
    )
    obs = DataValidator.from_file(DATA_VALIDATION_TEST_DIR / "simple_validation.yaml")
    assert obs == exp
