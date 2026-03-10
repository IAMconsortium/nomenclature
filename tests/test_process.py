import re
from pathlib import Path

import pytest

from nomenclature.definition import DataStructureDefinition
from nomenclature import process
from nomenclature.exceptions import DataValidationError

here = Path(__file__).parent
TEST_DATA_DIR = here / "data" / "definitions"


def test_process_definitions_data_validation_passes(simple_df):
    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    process(simple_df, definition)


def test_process_definitions_data_validation_fails(simple_df, caplog):
    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    simple_df._data.loc[
        ("model_a", "scen_a", "World", "Primary Energy", "EJ/yr", 2010)
    ] = -1

    message = re.escape(
        "Data validation failed with error(s) (file: definitions):\n"
        "  Criteria: variable: ['Primary Energy'], lower_bound: 0.0\n"
        "       model scenario region        variable   unit  year  value warning_level\n"
        "  0  model_a   scen_a  World  Primary Energy  EJ/yr  2010   -1.0         error\n"
    )
    with pytest.raises(DataValidationError, match=message):
        process(simple_df, definition)
