import pytest
from nomenclature.processor.meta import MetaValidator
from pathlib import Path
from conftest import TEST_DATA_DIR
import pyam

MODULE_TEST_DATA_DIR = TEST_DATA_DIR / "meta_validator"


def test_MetaValidator(simple_df):
    meta_validator = MetaValidator(MODULE_TEST_DATA_DIR / "definitions1" / "meta")
    exp = simple_df.copy()
    pyam.testing.assert_iamframe_equal(exp, meta_validator.apply(df=simple_df))


def test_MetaValidator_Meta_Indicator_Error(simple_df):
    simple_df.set_meta(name="not allowed", meta=False)
    meta_validator = MetaValidator(MODULE_TEST_DATA_DIR / "definitions2" / "meta")
    match = (
        "Invalid meta indicator: 'not allowed'\n"  # noqa
        "Valid meta indicators: 'boolean', 'number', 'string'"  # noqa
    )

    with pytest.raises(ValueError, match=match):
        meta_validator.apply(df=simple_df)


def test_MetaValidator_Meta_Indicator_Value_Error(simple_df):
    simple_df.set_meta(name="meta_string", meta=3)
    meta_validator = MetaValidator(MODULE_TEST_DATA_DIR / "definitions3" / "meta")
    match = (
        "Invalid value for meta indicator 'meta_string': '3'\n"  # noqa
        "Allowed values: 'A', 'B'"  # noqa
    )
    with pytest.raises(ValueError, match=match):
        meta_validator.apply(df=simple_df)
