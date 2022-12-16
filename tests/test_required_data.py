import pandas as pd
import pytest
from conftest import TEST_DATA_DIR

from pyam import assert_iamframe_equal
from nomenclature import DataStructureDefinition, RequiredDataValidator
from nomenclature.error.required_data import RequiredDataMissingError

REQUIRED_DATA_TEST_DIR = TEST_DATA_DIR / "required_data" / "required_data"


def test_RequiredDataValidator_from_file():

    exp = {
        "name": "MAGICC",
        "required_data": [
            {
                "variable": ["Emissions|CO2"],
                "region": ["World"],
                "year": [2020, 2030, 2040, 2050],
                "unit": None,
            },
        ],
        "file": REQUIRED_DATA_TEST_DIR / "requiredData.yaml",
    }

    obs = RequiredDataValidator.from_file(REQUIRED_DATA_TEST_DIR / "requiredData.yaml")

    assert obs.dict() == exp


def test_RequiredDataValidator_validate_with_definition():

    rdv = RequiredDataValidator.from_file(REQUIRED_DATA_TEST_DIR / "requiredData.yaml")
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "required_data" / "definition",
        dimensions=["region", "variable"],
    )
    rdv.validate_with_definition(dsd) is None


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

    rdv = RequiredDataValidator.from_file(REQUIRED_DATA_TEST_DIR / requiredDataFile)
    dsd = DataStructureDefinition(
        TEST_DATA_DIR / "required_data" / "definition",
        dimensions=["region", "variable"],
    )

    with pytest.raises(ValueError, match=match):
        rdv.validate_with_definition(dsd)


def test_RequiredData_apply(simple_df):
    # all good no warnings
    rdv = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / "requiredData_apply_working.yaml"
    )
    assert_iamframe_equal(rdv.apply(simple_df), simple_df)


def test_RequiredData_apply_raises(simple_df, caplog):

    rdv = RequiredDataValidator.from_file(
        REQUIRED_DATA_TEST_DIR / "requiredData_apply_error.yaml"
    )
    # assert that the correct error is raised
    with pytest.raises(RequiredDataMissingError, match="Required data missing"):
        rdv.apply(simple_df)

    missing_index = pd.DataFrame(
        [["model_a", "scen_a"], ["model_a", "scen_b"]], columns=["model", "scenario"]
    )
    # check if the log message contains the correct information
    assert all(
        x in caplog.text
        for x in ("ERROR", "Required data", "missing", str(missing_index))
    )
