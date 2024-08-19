import pandas as pd
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

    dsd = DataStructureDefinition(TEST_DATA_DIR / "validation" / "definitions")
    assert obs.validate_with_definition(dsd) is None


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
        DATA_VALIDATION_TEST_DIR / f"validate_unknown_{dimension}.yaml"
    )

    # validating against a DataStructure with all dimensions raises
    dsd = DataStructureDefinition(TEST_DATA_DIR / "validation" / "definitions")
    with pytest.raises(ValueError, match=match):
        data_validator.validate_with_definition(dsd)

    # validating against a DataStructure without the offending dimension passes
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "validation" / "definitions",
        dimensions=[dim for dim in ["region", "variable"] if dim != dimension],
    )
    assert data_validator.validate_with_definition(dsd) is None


def test_DataValidator_apply_no_matching_data(simple_df):
    data_validator = DataValidator.from_file(
        DATA_VALIDATION_TEST_DIR / "simple_validation.yaml"
    )
    # no data matches validation criteria, `apply()` passes and returns unchanged object
    assert data_validator.apply(simple_df) == simple_df


def test_DataValidator_apply_fails(simple_df, caplog):
    data_validator = DataValidator.from_file(
        DATA_VALIDATION_TEST_DIR / "validate_data_fails.yaml"
    )

    # TODO implement a utility function to display pandas nicely
    pd.set_option("display.width", 180)

    failed_validation_message = """Failed data validation (file data/validation/validate_data/validate_data_fails.yaml):
  Criteria: variable: ['Primary Energy'], upper_bound: 5.0
         model scenario region        variable   unit  year  value
    0  model_a   scen_a  World  Primary Energy  EJ/yr  2010    6.0
    1  model_a   scen_b  World  Primary Energy  EJ/yr  2010    7.0

  Criteria: variable: ['Primary Energy|Coal'], lower_bound: 2.0
         model scenario region             variable   unit  year  value
    0  model_a   scen_a  World  Primary Energy|Coal  EJ/yr  2005    0.5

  Criteria: variable: ['Primary Energy'], year: [2005], upper_bound: 1.9, lower_bound: 1.1
         model scenario region        variable   unit  year  value
    0  model_a   scen_a  World  Primary Energy  EJ/yr  2005    1.0
    1  model_a   scen_b  World  Primary Energy  EJ/yr  2005    2.0"""

    with pytest.raises(ValueError, match="Data validation failed"):
        data_validator.apply(simple_df)

    # check if the log message contains the correct information
    assert failed_validation_message in caplog.text
