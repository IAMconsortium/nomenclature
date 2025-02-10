from pathlib import Path

import pandas as pd
import pyam
import pydantic
import pytest


from pyam import IamDataFrame
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
            "Non-unique target and component \['Primary Energy'\] in aggregation-",
        ),
    ],
)
def test_aggregator_raises(file, error_msg_pattern):
    # This is to test different failure conditions
    with pytest.raises(pydantic.ValidationError, match=f"{error_msg_pattern}.*{file}"):
        Aggregator.from_file(TEST_FOLDER_GENERIC_PROCESSOR / file)


def test_aggregator_validate_with_definition():
    # Validate the Aggregator against the codelist in a DataStructureDefintion
    aggregator = Aggregator.from_file(
        TEST_FOLDER_GENERIC_PROCESSOR / "aggregation_mapping.yaml"
    )
    definition = DataStructureDefinition(TEST_FOLDER_GENERIC_PROCESSOR / "definition")
    aggregator.validate_with_definition(definition)


def test_aggregator_validate_invalid_code():
    file = "aggregation_mapping_invalid_code.yaml"
    aggregator = Aggregator.from_file(TEST_FOLDER_GENERIC_PROCESSOR / file)
    definition = DataStructureDefinition(TEST_FOLDER_GENERIC_PROCESSOR / "definition")
    match = f"The following variables are not .*\n .*- Final Energy\|Foo\n.*{file}"
    with pytest.raises(ValueError, match=match):
        aggregator.validate_with_definition(definition)


def test_aggregator_validate_invalid_dimension():
    file = "aggregation_mapping_invalid_dimension.yaml"
    aggregator = Aggregator.from_file(TEST_FOLDER_GENERIC_PROCESSOR / file)
    definition = DataStructureDefinition(TEST_FOLDER_GENERIC_PROCESSOR / "definition")
    match = f"Dimension 'foo' not found in DataStructureDefinition\nin.*{file}"
    with pytest.raises(ValueError, match=match):
        aggregator.validate_with_definition(definition)


def test_aggregator_apply():
    aggregator = Aggregator.from_file(
        TEST_FOLDER_GENERIC_PROCESSOR / "aggregation_mapping.yaml"
    )
    iamc_args = dict(model="model_a", scenario="scenario_a", region="World")

    df = IamDataFrame(
        pd.DataFrame(
            [
                ["Primary Energy|Coal", "EJ/yr", 0.5, 3],
                ["Primary Energy|Biomass", "EJ/yr", 2, 7],
                ["Final Energy|Electricity", "EJ/yr", 2.5, 3],
                ["Final Energy|Heat", "EJ/yr", 3, 6],
            ],
            columns=["variable", "unit", 2005, 2010],
        ),
        **iamc_args,
    )
    exp = IamDataFrame(
        pd.DataFrame(
            [
                ["Primary Energy", "EJ/yr", 2.5, 10],
                ["Final Energy", "EJ/yr", 5.5, 9],
            ],
            columns=["variable", "unit", 2005, 2010],
        ),
        **iamc_args,
    )
    pyam.assert_iamframe_equal(aggregator.apply(df), exp)
