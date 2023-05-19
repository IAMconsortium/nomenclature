import pytest
import pandas as pd
import pyam
from nomenclature.processor.meta import MetaValidator
from pathlib import Path
from conftest import TEST_DATA_DIR


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
    path = Path(TEST_DATA_DIR / "definitions/meta/meta_indicators_allowed_values.yaml")
    df = pyam.IamDataFrame(DF)
    assert df == MetaValidator.validate_meta_indicators(df=df, path=path)


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
    path = Path(TEST_DATA_DIR / "definitions/meta/meta_indicators_test_data.yaml")
    df = pyam.IamDataFrame(DF)

    match = (
        "['exclude'] is/are not recognized in the meta "
        "definitions file at tests\data\definitions\meta\meta_indicators_test_data.yaml"
    )
    with pytest.raises(ValueError, match=match):
        MetaValidator.validate_meta_indicators(df=df, path=path)


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
    path = Path(TEST_DATA_DIR / "definitions/meta/meta_indicators_more_data.yaml")
    df = pyam.IamDataFrame(DF)

    match = (
        "[False, False] meta indicator value(s) in the "
        "exclude column are not allowed. Allowed values are ['A', 'B']"
    )

    with pytest.raises(ValueError, match=match):
        MetaValidator.validate_meta_indicators(df=df, path=path)
