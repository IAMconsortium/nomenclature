import pytest
import pandas as pd
import pyam
from nomenclature.processor.meta import MetaValidator
from pathlib import Path
from conftest import TEST_DATA_DIR
import re


def test_MetaValidator():
    TEST_YEARS = [2005, 2010]
    DF = pd.DataFrame(
        [
            ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 1, 6.0],
            ["model_a", "scen_a", "World", "Primary Energy|Coal", "EJ/yr", 0.5, 3],
            ["model_a", "scen_b", "World", "Primary Energy", "EJ/yr", 2, 7],
        ],
        columns=pyam.IAMC_IDX + TEST_YEARS,
    )
    path = Path(TEST_DATA_DIR / "definitions1/meta")
    df = pyam.IamDataFrame(DF)
    mv = MetaValidator()
    assert df == mv.validate_meta_indicators(df=df, path=path)


def test_MetaValidator_Meta_Indicator_Error():
    TEST_YEARS = [2005, 2010]
    DF = pd.DataFrame(
        [
            ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 1, 6.0],
            ["model_a", "scen_a", "World", "Primary Energy|Coal", "EJ/yr", 0.5, 3],
            ["model_a", "scen_b", "World", "Primary Energy", "EJ/yr", 2, 7],
        ],
        columns=pyam.IAMC_IDX + TEST_YEARS,
    )
    path = Path(TEST_DATA_DIR / "definitions2/meta")
    df = pyam.IamDataFrame(DF)
    mv = MetaValidator()
    match = (
        "['exclude'] is/are not recognized in the meta "
        "definitions file at h:\\nomenclature\\tests\\data\\definitions2\\meta"  # noqa
    )
    with pytest.raises(ValueError) as exc:
        mv.validate_meta_indicators(df=df, path=path)

    assert str(exc.value) == match


def test_MetaValidator_Meta_Indicator_Value_Error():
    TEST_YEARS = [2005, 2010]
    DF = pd.DataFrame(
        [
            ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 1, 6.0],
            ["model_a", "scen_a", "World", "Primary Energy|Coal", "EJ/yr", 0.5, 3],
            ["model_a", "scen_b", "World", "Primary Energy", "EJ/yr", 2, 7],
        ],
        columns=pyam.IAMC_IDX + TEST_YEARS,
    )
    path = Path(TEST_DATA_DIR / "definitions3/meta")
    df = pyam.IamDataFrame(DF)
    mv = MetaValidator()
    match = (
        "[False, False] meta indicator value(s) in the "
        "exclude column are not allowed. Allowed values are ['A', 'B']"
    )

    with pytest.raises(ValueError, match=re.escape(match)):
        mv.validate_meta_indicators(df=df, path=path)
