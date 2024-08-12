import pytest
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

    dsd = DataStructureDefinition(TEST_DATA_DIR / "validation" / "definition")
    obs.validate_with_definition(dsd) is None


@pytest.mark.parametrize(
    "dimension, match",
    [
        ("region", r"regions.*not defined.*\n.*Asia"),
        ("variable", r"variables.*not defined.*\n.*Final Energy\|Industry"),
    ],
)
def test_DataValidator_validate_with_definition_raises(dimension, match):
    # Testing two different failure cases
    # 1. Undefined region
    # 2. Undefined variable
    # TODO Undefined unit

    data_validator = DataValidator.from_file(
        DATA_VALIDATION_TEST_DIR / f"validation_unknown_{dimension}.yaml"
    )

    # validating against a DataStructure with all dimensions raises
    dsd = DataStructureDefinition(TEST_DATA_DIR / "validation" / "definition")
    with pytest.raises(ValueError, match=match):
        data_validator.validate_with_definition(dsd)

    # validating against a DataStructure without the offending dimension passes
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "validation" / "definition",
        dimensions=[dim for dim in ["region", "variable"] if dim != dimension]
    )
    assert data_validator.validate_with_definition(dsd) is None
