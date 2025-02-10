from pathlib import Path

import pydantic
import pytest

from conftest import TEST_DATA_DIR
from nomenclature import DataStructureDefinition
from nomenclature.processor import Aggregator

TEST_FOLDER_GENERIC_PROCESSOR = TEST_DATA_DIR / "processor" / "generic"


def test_aggregator_from_file():
    mapping_file = "aggregation_mapping.yaml"
    # Test that the file is read and represented correctly
    obs = Aggregator.from_file(TEST_FOLDER_GENERIC_PROCESSOR / mapping_file)
    exp = {
        "file": (TEST_FOLDER_GENERIC_PROCESSOR / mapping_file).relative_to(Path.cwd()),
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
        (
            "aggregation_mapping_duplicate_component.yaml",
            "Duplicate component \['Primary Energy\|Coal'\] in aggregation-mapping in ",
        ),
        (
            "aggregation_mapping_target_component_conflict.yaml",
            "Non-unique target and component \['Primary Energy'\] in aggregation-"
        ),
    ],
)
def test_aggregator_raises(file, error_msg_pattern):
    # This is to test a few different failure conditions

    with pytest.raises(pydantic.ValidationError, match=f"{error_msg_pattern}.*{file}"):
        Aggregator.from_file(TEST_FOLDER_GENERIC_PROCESSOR / file)


def test_aggregator_validate_with_definition():
    obs = Aggregator.from_file(
        TEST_FOLDER_GENERIC_PROCESSOR / "aggregation_mapping.yaml"
    )
    definition = DataStructureDefinition(TEST_FOLDER_GENERIC_PROCESSOR / "definition")
    obs.validate_with_definition(definition)


def test_aggregator_validate_with_definition_raises():
    file = "aggregation_mapping_invalid_code.yaml"
    obs = Aggregator.from_file(TEST_FOLDER_GENERIC_PROCESSOR / file)
    definition = DataStructureDefinition(TEST_FOLDER_GENERIC_PROCESSOR / "definition")
    match = f"The following variables are not .*\n .*- Final Energy\|Foo\n.*{file}"
    with pytest.raises(ValueError, match=match):
       obs.validate_with_definition(definition)
