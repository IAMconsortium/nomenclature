# tests/test_nuts_aggregation.py
import pandas as pd
from pathlib import Path
from pyam import IamDataFrame, assert_iamframe_equal
from pyam.utils import IAMC_IDX

from nomenclature import DataStructureDefinition
from nomenclature.processor.nuts import NutsProcessor

here = Path(__file__).parent
TEST_DATA_DIR = here / "data"
NUTS_TEST_DIR = TEST_DATA_DIR / "nuts_processing" / "dsd"


def test_nuts_simple_aggregation():
    """Test basic NUTS3 -> NUTS2 -> NUTS1 -> Country aggregation"""

    # Create test data with NUTS3 regions (Austria)
    # AT111, AT112 should aggregate to AT11 (NUTS2) -> AT1 (NUTS1) -> Austria
    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "AT111", "Primary Energy", "EJ/yr", 1.0, 2.0],
                ["model_a", "scen_a", "AT112", "Primary Energy", "EJ/yr", 3.0, 4.0],
                ["model_a", "scen_a", "Belgium", "Primary Energy", "EJ/yr", 5.0, 6.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    # Expected output: aggregated to Austria
    expected = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "Austria", "Primary Energy", "EJ/yr", 4.0, 6.0],
                ["model_a", "scen_a", "Belgium", "Primary Energy", "EJ/yr", 5.0, 6.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    # Load DSD and apply NUTS processor
    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)

    result = processor.apply(test_df)

    assert_iamframe_equal(result, expected)
