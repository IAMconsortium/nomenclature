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
    path = Path(TEST_DATA_DIR / "definitions2/meta")
    meta_validator = MetaValidator(path_to_meta_code_list_files=path)
    match = (
        "\['exclude'\] is/are not recognized in the meta definitions file. "  # noqa
        "Allowed meta indicators are: \['Not exclude', 'number', 'string'\]"  # noqa
    )

    with pytest.raises(ValueError, match=match):
        meta_validator.apply(df=simple_df)


def test_MetaValidator_Meta_Indicator_Value_Error(simple_df):
    path = Path(TEST_DATA_DIR / "definitions3/meta")
    meta_validator = MetaValidator(path_to_meta_code_list_files=path)
    match = (
        "\[False\] meta indicator value\(s\) in the "  # noqa
        "exclude column are not allowed. Allowed values are \['A', 'B'\]"  # noqa
    )
    with pytest.raises(ValueError, match=match):
        meta_validator.apply(df=simple_df)
