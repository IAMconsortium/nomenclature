from pathlib import Path
from typing import Dict, List
import pytest
import numpy as np
import pandas as pd
from pyam import IamDataFrame, IAMC_IDX
from nomenclature import DataStructureDefinition
from nomenclature.code import Code


here = Path(__file__).parent
TEST_DATA_DIR = here / "data"


TEST_DF = pd.DataFrame(
    [
        ["model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 1, 6.0],
        ["model_a", "scen_a", "World", "Primary Energy|Coal", "EJ/yr", 0.5, 3],
        ["model_a", "scen_b", "World", "Primary Energy", "EJ/yr", 2, 7],
    ],
    columns=IAMC_IDX + [2005, 2010],
)


@pytest.fixture(scope="session")
def simple_definition():
    yield DataStructureDefinition(TEST_DATA_DIR / "validation_nc")


@pytest.fixture(scope="session")
def extras_definition():
    yield DataStructureDefinition(TEST_DATA_DIR / "extras_nc")


@pytest.fixture(scope="function")
def simple_df():
    df = IamDataFrame(TEST_DF)
    add_meta(df)
    yield df


def add_meta(df):
    """Add simple meta indicators"""
    if len(df.index) == 1:
        df.set_meta([1.0], "number")
        df.set_meta(["foo"], "string")
    if len(df.index) == 2:
        df.set_meta([1.0, 2.0], "number")
        df.set_meta(["foo", np.nan], "string")


def remove_file_from_mapping(mapping: Dict[str, Code]) -> List[Dict]:
    return [
        {key: value for key, value in code.flattened_dict.items() if key != "file"}
        for code in mapping.values()
    ]
