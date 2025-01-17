from pathlib import Path

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
    "name, match",
    [
        ("missing_criteria", "No validation criteria provided:"),
        ("bounds_and_value", "Cannot use bounds and value-criteria simultaneously:"),
        ("bounds_and_rtol", "Cannot use bounds and value-criteria simultaneously:"),
    ],
)
def test_DataValidator_illegal_structure(name, match):
    with pytest.raises(ValueError, match=match):
        DataValidator.from_file(DATA_VALIDATION_TEST_DIR / f"validate_{name}.yaml")


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


@pytest.mark.parametrize(
    "file, item_1, item_2, item_3",
    [
        (
            "bounds",
            "upper_bound: 5.0",
            "lower_bound: 2.0",
            "upper_bound: 1.9, lower_bound: 1.1",
        ),
        (
            "value",
            "value: 2.0, atol: 1.0",
            "value: 3.0",
            "value: 1.5, rtol: 0.2",
        ),
    ],
)
def test_DataValidator_apply_fails(simple_df, file, item_1, item_2, item_3, caplog):
    data_file = DATA_VALIDATION_TEST_DIR / f"validate_data_fails_{file}.yaml"
    data_validator = DataValidator.from_file(data_file)

    failed_validation_message = (
        "Data validation with error(s)/warning(s) "
        f"""(file {data_file.relative_to(Path.cwd())}):
  Criteria: variable: ['Primary Energy'], {item_1}
         model scenario region        variable   unit  year  value warning_level
    0  model_a   scen_a  World  Primary Energy  EJ/yr  2010    6.0         error
    1  model_a   scen_b  World  Primary Energy  EJ/yr  2010    7.0         error

  Criteria: variable: ['Primary Energy|Coal'], {item_2}
         model scenario region  ...  year value  warning_level
    0  model_a   scen_a  World  ...  2005   0.5          error

    [1 rows x 8 columns]

  Criteria: variable: ['Primary Energy'], year: [2005], {item_3}
         model scenario region        variable   unit  year  value warning_level
    0  model_a   scen_a  World  Primary Energy  EJ/yr  2005    1.0         error
    1  model_a   scen_b  World  Primary Energy  EJ/yr  2005    2.0         error"""
    )

    with pytest.raises(ValueError, match="Data validation failed"):
        data_validator.apply(simple_df)

    # check if the log message contains the correct information
    assert failed_validation_message in caplog.text


def test_DataValidator_validate_with_warning(simple_df, caplog):
    data_validator = DataValidator.from_file(
        DATA_VALIDATION_TEST_DIR / "validate_warning.yaml"
    )
    with pytest.raises(ValueError, match="Data validation failed"):
        data_validator.apply(simple_df)

    failed_validation_message = (
        "Data validation with error(s)/warning(s) "
        f"""(file {(DATA_VALIDATION_TEST_DIR / "validate_warning.yaml").relative_to(Path.cwd())}):
  Criteria: variable: ['Primary Energy'], year: [2010], upper_bound: 2.5, lower_bound: 1.0
         model scenario region        variable   unit  year  value warning_level
    0  model_a   scen_a  World  Primary Energy  EJ/yr  2010    6.0           low
    1  model_a   scen_b  World  Primary Energy  EJ/yr  2010    7.0           low

  Criteria: variable: ['Primary Energy'], year: [2010], upper_bound: 5.0, lower_bound: 1.0
         model scenario region        variable   unit  year  value warning_level
    0  model_a   scen_a  World  Primary Energy  EJ/yr  2010    6.0         error
    1  model_a   scen_b  World  Primary Energy  EJ/yr  2010    7.0         error"""
    )

    # only prints two of three criteria in df to be validated
    assert failed_validation_message in caplog.text
