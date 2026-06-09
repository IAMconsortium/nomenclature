import re
from pathlib import Path

import pytest
from pyam import IamDataFrame

from nomenclature.definition import DataStructureDefinition
from nomenclature import process
from nomenclature.exceptions import DataValidationError
from nomenclature.processor import Processor

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


def test_process_with_failing_processor_raises(simple_df):
    """Test that a failing processor without fail_ok raises an error"""

    class FailingProcessor(Processor):
        def apply(self, df: IamDataFrame) -> IamDataFrame:
            raise ValueError("Intentional test error")

    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    failing_processor = FailingProcessor()

    with pytest.raises(ValueError, match="Intentional test error"):
        process(simple_df, definition, processor=failing_processor)


def test_process_with_failing_processor_fail_ok_continues(simple_df, caplog):
    """Test that a failing processor with fail_ok=True continues processing"""

    class FailingProcessor(Processor):
        def apply(self, df: IamDataFrame) -> IamDataFrame:
            raise ValueError("Intentional test error")

    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    failing_processor = FailingProcessor(fail_ok=True)

    # Should not raise, should continue processing
    result = process(simple_df, definition, processor=failing_processor)

    # The result should be the original dataframe since the processor failed
    assert result.equals(simple_df)

    # Check that a warning was logged
    assert "FailingProcessor failed with error: Intentional test error" in caplog.text
    assert "Continuing with processing as fail_ok=True" in caplog.text


def test_process_with_multiple_processors_one_fails(simple_df, caplog):
    """Test that with multiple processors, one can fail and others still run"""

    class FailingProcessor(Processor):
        def apply(self, df: IamDataFrame) -> IamDataFrame:
            raise ValueError("Intentional test error")

    class SuccessfulProcessor(Processor):
        def apply(self, df: IamDataFrame) -> IamDataFrame:
            return df

    definition = DataStructureDefinition(TEST_DATA_DIR / "definitions_with_validation")
    processors = [
        FailingProcessor(fail_ok=True),
        SuccessfulProcessor(),
    ]

    # Should not raise, should continue processing
    result = process(simple_df, definition, processor=processors)

    # Check that a warning was logged for the failed processor
    assert "FailingProcessor failed with error: Intentional test error" in caplog.text
    assert "Continuing with processing as fail_ok=True" in caplog.text

    # Result should still be valid (second processor returned the df unchanged)
    assert result.equals(simple_df)
