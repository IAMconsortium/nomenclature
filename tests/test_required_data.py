from copy import deepcopy
import pandas as pd
import pytest
from conftest import TEST_DATA_DIR

from pyam import assert_iamframe_equal
from nomenclature import DataStructureDefinition, RequiredDataValidator
from nomenclature.processor.required_data import RequiredMeasurand
from nomenclature.error.required_data import RequiredDataMissingError

REQUIRED_DATA_TEST_DIR = TEST_DATA_DIR / "required_data" / "required_data"


def test_RequiredDataValidator_from_file():
    exp = {
        "description": "Required variables for running MAGICC",
        "model": ["model_a"],
        "required_data": [
            {
                "measurand": [
                    RequiredMeasurand(variable="Emissions|CO2", unit="Mt CO2/yr")
                ],
                "region": ["World"],
                "year": [2020, 2030, 2040, 2050],
            },
        ],
        "file": REQUIRED_DATA_TEST_DIR / "requiredData.yaml",
    }

    obs = RequiredDataValidator.from_file(REQUIRED_DATA_TEST_DIR / "requiredData.yaml")

    assert obs.dict(exclude_unset=True) == exp


def test_RequiredDataValidator_validate_with_definition():
    required_data_validator = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / "requiredData.yaml"
    )
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "required_data" / "definition",
        dimensions=["region", "variable"],
    )
    required_data_validator.validate_with_definition(dsd) is None


@pytest.mark.parametrize(
    "requiredDataFile, match",
    [
        ("requiredData_unknown_region.yaml", r"region\(s\).*not found.*\n.*Asia"),
        (
            "requiredData_unknown_variable.yaml",
            r"variable\(s\).*not found.*\n.*Final Energy\|Industry",
        ),
        (
            "requiredData_unknown_unit.yaml",
            r"wrong unit.*\n.*'Final Energy', 'Mtoe\/yr', 'EJ\/yr'",
        ),
    ],
)
def test_RequiredDataValidator_validate_with_definition_raises(requiredDataFile, match):
    # Testing three different failure cases
    # 1. Undefined region
    # 2. Undefined variable
    # 3. Undefined unit

    required_data_validator = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / requiredDataFile
    )
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "required_data" / "definition",
        dimensions=["region", "variable"],
    )

    with pytest.raises(ValueError, match=match):
        required_data_validator.validate_with_definition(dsd)


@pytest.mark.parametrize(
    "required_data_file",
    [
        "requiredData_apply_working.yaml",
        "requiredData_any_unit.yaml",
        "requiredData_multiple_units_allowed.yaml",
    ],
)
def test_RequiredData_apply(simple_df, required_data_file):
    # all good no warnings
    required_data_validator = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / required_data_file
    )
    assert_iamframe_equal(required_data_validator.apply(simple_df), simple_df)


def test_RequiredData_apply_raises(simple_df, caplog):
    required_data_validator = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / "requiredData_apply_error.yaml"
    )
    # assert that the correct error is raised
    with pytest.raises(RequiredDataMissingError, match="Required data missing"):
        required_data_validator.apply(simple_df)

    missing_index = pd.DataFrame(
        [["model_a", "scen_a"], ["model_a", "scen_b"]], columns=["model", "scenario"]
    )
    # check if the log message contains the correct information
    assert all(
        x in caplog.text
        for x in ("ERROR", "Required data", "missing", str(missing_index))
    )


def test_per_model_RequiredData(simple_df):
    # required data is missing but it's only required for model_a
    # therefore this should return the dataframe intact
    required_data_validator = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / "requiredData_apply_error.yaml"
    )
    simple_df = simple_df.rename(model={"model_a": "model_b"})
    exp = deepcopy(simple_df)
    assert_iamframe_equal(exp, required_data_validator.apply(simple_df))
