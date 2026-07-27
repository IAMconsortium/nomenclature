from nomenclature.processor.validator import WarningEnum
from nomenclature.codelist import MetaCodeList
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor.meta import MetaValidator

from conftest import TEST_DATA_DIR

MODULE_TEST_DATA_DIR = TEST_DATA_DIR / "meta_validator"


def test_MetaValidator_from_codelist(simple_df):
    """
    Test MetaValidator can be created from a MetaCodeList and validation criteria
    are set correctly.
    """
    meta_codelist = MetaCodeList.from_directory(
        "meta", MODULE_TEST_DATA_DIR / "definitions1" / "meta"
    )
    meta_validator = MetaValidator.from_codelist(meta_codelist)
    assert meta_validator.criteria_items[0].validation[0].value == [True, False]
    assert meta_validator.criteria_items[1].validation[0].value == [1.0, 2.0, 3.0, 4.0]
    assert meta_validator.criteria_items[2].validation[0].value == ["foo", "bar"]


def test_MetaValidator_from_file(simple_df):
    """
    Test MetaValidator can be created from a YAML file and validation criteria
    are set correctly.
    """
    meta_validator = MetaValidator.from_file(
        MODULE_TEST_DATA_DIR / "validate_meta" / "meta.yaml"
    )
    assert meta_validator.criteria_items[0].validation[0].upper_bound == 2.0
    assert (
        meta_validator.criteria_items[0].validation[0].warning_level == WarningEnum.high
    )
    assert meta_validator.criteria_items[1].validation[0].value == ["foo"]


def test_MetaValidator_validate_with_definition(simple_df):
    """
    Test MetaValidator's criteria items against the MetaCodeList."""
    meta_codelist = MetaCodeList.from_directory(
        "meta", MODULE_TEST_DATA_DIR / "definitions1" / "meta"
    )
    meta_validator = MetaValidator.from_codelist(meta_codelist)
    dsd = DataStructureDefinition(MODULE_TEST_DATA_DIR / "definitions1")
    meta_validator.validate_with_definition(dsd)
