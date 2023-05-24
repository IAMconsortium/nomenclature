import pytest
from nomenclature.processor.meta import MetaValidator
from pathlib import Path
from conftest import TEST_DATA_DIR, simple_df
import pyam


def test_MetaValidator():
    path = Path(TEST_DATA_DIR / "definitions1/meta")
    exp = simple_df.copy()
    pyam.testing.assert_iamframe_equal(
        exp, MetaValidator.apply(df=simple_df, path=path)
    )


def test_MetaValidator_Meta_Indicator_Error():
    path = Path(TEST_DATA_DIR / "definitions2/meta")
    match = (
        r"\['exclude'\] is/are not recognized in the meta "
        r"definitions file at .*\\definitions2\\meta"  # noqa
    )

    with pytest.raises(ValueError, match=match):
        MetaValidator.apply(df=simple_df, path=path)


def test_MetaValidator_Meta_Indicator_Value_Error():
    path = Path(TEST_DATA_DIR / "definitions3/meta")
    match = (
        "\[False, False\] meta indicator value\(s\) in the "  # noqa
        "exclude column are not allowed. Allowed values are \['A', 'B'\]"  # noqa
    )

    with pytest.raises(ValueError, match=match):
        MetaValidator.apply(df=simple_df, path=path)
