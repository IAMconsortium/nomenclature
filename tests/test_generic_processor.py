from pathlib import Path

import pydantic
import pytest

from conftest import TEST_DATA_DIR
from nomenclature.processor import Aggregator

TEST_FOLDER_SIMPLE_PROCESSOR = TEST_DATA_DIR / "processor" / "generic"


def test_Aggregator_from_file():
    mapping_file = "aggregation_mapping.yaml"
    # Test that the file is read and represented correctly
    obs = Aggregator.from_file(TEST_FOLDER_SIMPLE_PROCESSOR / mapping_file)
    exp = {
        "file": (TEST_FOLDER_SIMPLE_PROCESSOR / mapping_file).relative_to(Path.cwd()),
        "dimension": "variable",
        "mapping": [
            {
                "name": "Primary Energy",
                "components": ["Primary Energy|Coal", "Primary Energy|Biomass"],
            },
            {
                "name": "Final Energy",
                "components": ["Final Energy|Electricity", "Final Energy|Heat"],
            },
        ],
    }
    assert obs.model_dump() == exp


@pytest.mark.parametrize(
    "file, error_msg_pattern",
    [
        (
            "aggregation_mapping_duplicate_target.yaml",
            "Duplicate target \['Primary Energy'\] in aggregation-mapping in ",
        ),
    ],
)
def test_Aggregator_raises(file, error_msg_pattern):
    # This is to test a few different failure conditions

    with pytest.raises(pydantic.ValidationError, match=f"{error_msg_pattern}.*{file}"):
        Aggregator.from_file(TEST_FOLDER_SIMPLE_PROCESSOR / file)
