import pytest
import pandas as pd

from pyam import IamDataFrame
from pyam.utils import IAMC_IDX
from nomenclature.processor.validator import WarningEnum
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.meta_validator import MetaValidator
from nomenclature.exceptions import (
    NoTracebackException,
    MetaValidationError,
)

from conftest import TEST_DATA_DIR

MODULE_TEST_DATA_DIR = TEST_DATA_DIR / "meta_validator"


def test_MetaValidator_from_file():
    """Check that a MetaValidator can be created from a yaml file"""
    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_multiple.yaml"
    )
    criteria_item_0 = meta_validator.criteria_items[0]
    assert criteria_item_0.validation[0].upper_bound == 1.0
    assert criteria_item_0.validation[0].warning_level == WarningEnum.high
    assert criteria_item_0.validation[1].upper_bound == 0.0
    assert criteria_item_0.validation[1].warning_level == WarningEnum.medium

    criteria_item_1 = meta_validator.criteria_items[1]
    assert criteria_item_1.validation[0].value == ["foo"]
    assert criteria_item_1.validation[0].warning_level == WarningEnum.low


def test_MetaValidator_validate_with_definition():
    """
    Test MetaValidator's criteria items against the MetaCodeList.
    """
    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_multiple.yaml"
    )
    dsd = DataStructureDefinition(MODULE_TEST_DATA_DIR / "definitions")

    assert meta_validator.validate_with_definition(dsd) is None


def test_MetaValidator_validate_with_definition_raises():
    """
    Test MetaValidator's DSD validation when criteria uses indicators not in definition.
    """
    error_msg = (
        "The following meta-indicators are not defined "
        "in the MetaCodeList:\n   'not defined'"
    )

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "indicator_not_defined.yaml"
    )
    dsd = DataStructureDefinition(MODULE_TEST_DATA_DIR / "definitions")

    with pytest.raises(NoTracebackException) as excinfo:
        meta_validator.validate_with_definition(dsd)
    assert excinfo.match(error_msg)


def test_MetaValidator_apply_warning(simple_df, caplog):
    """
    Test MetaValidator's criteria items against a data frame.
    """
    warning_msg = """  Criteria: meta: ['number'], upper_bound: 1.0
                    number warning_level
  model   scenario                      
  model_a scen_b       2.0          high"""

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_high.yaml"
    )
    meta_validator.apply(simple_df)
    assert warning_msg in caplog.text


def test_MetaValidator_apply_multiple_warning_levels(simple_df, caplog):
    """
    Test MetaValidator can apply multiple warning levels to meta-indicators.
    """
    warning_msg = """
  Criteria: meta: ['number'], upper_bound: 1.0
                    number warning_level
  model   scenario                      
  model_a scen_b       2.0          high

  Criteria: meta: ['number'], upper_bound: 0.0
                    number warning_level
  model   scenario                      
  model_a scen_a       1.0        medium

  Criteria: meta: ['string'], value: ['foo']
                   string warning_level
  model   scenario                     
  model_a scen_b      bar           low"""

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_multiple.yaml"
    )
    meta_validator.apply(simple_df)
    assert warning_msg in caplog.text


def test_MetaValidator_apply_value_tolerance(simple_df, caplog):
    """
    Test MetaValidator allows validation with value and tolerance for `value` field.
    """
    warning_msg = """  Criteria: meta: ['number'], value: 1.0, atol: 0.5
                    number warning_level
  model   scenario                      
  model_a scen_b       2.0        medium"""

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_value_tolerance.yaml"
    )
    meta_validator.apply(simple_df)
    assert warning_msg in caplog.text


def test_MetaValidator_apply_multiple_columns(simple_df, caplog):
    """
    Test MetaValidator allows simultaneous validation for multiple meta columns.
    Higher-level warnings are prioritised over lower-level warnings for the same scenario.
    """
    warning_msg = """  Criteria: meta: ['number', 'number_too'], upper_bound: 1.0
                    number  number_too warning_level
  model   scenario                                  
  model_a scen_a       1.0         2.0          high
          scen_b       2.0         1.0          high"""
    simple_df.set_meta([2.0, 1.0], "number_too")
    warning_msg = """"""
    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_multiple_columns.yaml"
    )
    meta_validator.apply(simple_df)
    assert warning_msg in caplog.text
    assert "upper_bound: 0.0" not in caplog.text
    assert "low" not in caplog.text


def test_MetaValidator_apply_empty_df(caplog):
    """
    Test MetaValidator on an empty data frame (columns but no rows).
    """
    empty_df = IamDataFrame(pd.DataFrame([], columns=IAMC_IDX + [2005, 2010]))
    empty_df.set_meta([], "number")

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_high.yaml"
    )
    meta_validator.apply(empty_df)

    assert (
        "Columns 'number' do not exist in `meta`, skipping validation." in caplog.text
    )

    empty_df.set_meta([], "number_too")
    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_multiple_columns.yaml"
    )
    meta_validator.apply(empty_df)

    assert (
        "Columns 'number', 'number_too' do not exist in `meta`, skipping validation."
        in caplog.text
    )


def test_MetaValidator_apply_ignore_missing_column(simple_df, caplog):
    """Test MetaValidator on a data frame with a missing meta-indicator."""
    warning_msg = """  Criteria: meta: ['number', 'number_too'], upper_bound: 1.0
                    number warning_level
  model   scenario                      
  model_a scen_b       2.0          high"""

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_multiple_columns.yaml"
    )
    meta_validator.apply(simple_df)
    assert warning_msg in caplog.text


def test_MetaValidator_apply_error(simple_df):
    """
    Test MetaValidator's criteria items against a data frame.
    """

    error_msg = """Criteria: meta: ['string'], value: ['foo']
                   string warning_level
  model   scenario                     
  model_a scen_b      bar         error"""

    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "warning_error.yaml"
    )
    with pytest.raises(MetaValidationError) as excinfo:
        meta_validator.apply(simple_df)
    assert error_msg in str(excinfo.value)


@pytest.mark.parametrize(
    "yaml_file, expected_count_message",
    [
        ("warning_high.yaml", "1 of 1 criteria failed validation (1 of 2 rows)."),
        ("warning_multiple.yaml", "2 of 2 criteria failed validation (2 of 2 rows)."),
    ],
)
def test_MetaValidator_apply_warning_count_message(
    simple_df, caplog, yaml_file, expected_count_message
):
    """
    Test MetaValidator logs the correct count of failed scenarios.
    Verifies count of failed validation criteria in the warning message is accurate.
    """
    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / yaml_file
    )
    meta_validator.apply(simple_df)
    assert expected_count_message in caplog.text
