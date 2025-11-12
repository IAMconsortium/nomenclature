from pathlib import Path

import pytest

from nomenclature.definition import DataStructureDefinition
from nomenclature import process

here = Path(__file__).parent
TEST_DATA_DIR = here / "data" / "definitions"


def test_process_definitions_data_validation_passes(simple_df):

    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    process(simple_df, definition)


def test_process_definitions_data_validation_fails(simple_df):

    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    simple_df._data.loc[
        ("model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 2010)
    ] = -1
    with pytest.raises(ValueError):
        process(simple_df, definition)
