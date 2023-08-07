import pytest
from nomenclature.processor.meta import MetaValidator
from pathlib import Path
from conftest import TEST_DATA_DIR
import pyam


def test_MetaValidator(simple_df):
    path = Path(TEST_DATA_DIR / "definitions1/meta")
    meta_validator = MetaValidator(path_to_meta_code_list_files=path)
    exp = simple_df.copy()
    pyam.testing.assert_iamframe_equal(exp, meta_validator.apply(df=simple_df))


def test_MetaValidator_Meta_Indicator_Error(simple_df):
    path = Path(TEST_DATA_DIR / "definitions2" / "meta")
    simple_df.set_meta(name="not allowed", meta=False)
    meta_validator = MetaValidator(path_to_meta_code_list_files=path)
    match = (
        "Invalid meta indicator: 'not allowed'\n"  # noqa
        "Valid meta indicators: 'boolean', 'number', 'string'"  # noqa
    )

    with pytest.raises(ValueError, match=match):
        meta_validator.apply(df=simple_df)


def test_MetaValidator_Meta_Indicator_Value_Error(simple_df):
    path = Path(TEST_DATA_DIR / "definitions3" / "meta")
    simple_df.set_meta(name="meta_string", meta=3)
    meta_validator = MetaValidator(path_to_meta_code_list_files=path)
    match = (
        "Invalid value for meta indicator 'meta_string': '3'\n"  # noqa
        "Allowed values: 'A', 'B'"  # noqa
    )
    with pytest.raises(ValueError, match=match):
        meta_validator.apply(df=simple_df)
