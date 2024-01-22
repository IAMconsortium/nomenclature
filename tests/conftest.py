import shutil
import sys
import os
import stat
from pathlib import Path

import pandas as pd
import pytest
from pyam import IamDataFrame
from pyam.utils import IAMC_IDX

from nomenclature import DataStructureDefinition

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
        df.set_meta(["foo", "bar"], "string")


def clean_up_external_repos(repos):
    # clean up the external repo
    for repository in repos.values():
        if repository.local_path.exists():
            if sys.platform.startswith("win") and not os.access(
                repository.local_path, os.W_OK
            ):
                os.chmod(repository.local_path, stat.S_IWUSR)
            shutil.rmtree(repository.local_path)  # , ignore_errors=True)
