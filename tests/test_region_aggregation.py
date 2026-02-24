from pathlib import Path

import pandas as pd
import pydantic
import pytest
from conftest import TEST_DATA_DIR, clean_up_external_repos
from pyam import IamDataFrame, assert_iamframe_equal
from pyam.utils import IAMC_IDX
from pydantic import ValidationError

from nomenclature import (
    DataStructureDefinition,
    RegionAggregationMapping,
    RegionProcessor,
    process,
)
from nomenclature.processor.region import CommonRegion, NativeRegion

TEST_FOLDER_REGION_PROCESSING = TEST_DATA_DIR / "region_processing"
TEST_FOLDER_REGION_AGGREGATION = TEST_FOLDER_REGION_PROCESSING / "region_aggregation"


def test_mapping():
    mapping_file = "working_mapping.yaml"
    # Test that the file is read and represented correctly
    obs = RegionAggregationMapping.from_file(
        TEST_FOLDER_REGION_AGGREGATION / mapping_file
    )
    exp = {
        "model": ["model_a"],
        "file": (TEST_FOLDER_REGION_AGGREGATION / mapping_file).relative_to(Path.cwd()),
        "native_regions": [
            {"name": "region_a", "rename": "alternative_name_a"},
            {"name": "region_b", "rename": "alternative_name_b"},
            {"name": "region_c", "rename": None},
        ],
        "common_regions": [
            {
                "name": "common_region_1",
                "constituent_regions": ["region_a", "region_b"],
            },
            {
                "name": "common_region_2",
                "constituent_regions": ["region_c"],
            },
        ],
        "exclude_regions": [],
    }
    assert obs.model_dump() == exp


@pytest.mark.parametrize(
    "file, error_msg_pattern",
    [
        (
            "illegal_mapping_conflict_regions.yaml",
            "Name collision in native and common regions.*common_region_1",
        ),
        (
            "illegal_mapping_native_duplicate_key_rename.yaml",
            "Name collision in native regions .names.*region_a",
        ),
        (
            "illegal_mapping_native_duplicate_key_keep.yaml",
            "Name collision in native regions .names.*region_a",
        ),
        (
            "illegal_mapping_native_rename_key_conflict.yaml",
            "Name collision in native regions .names.*region_a",
        ),
        (
            "illegal_mapping_native_rename_target_conflict_1.yaml",
            "Name collision in native regions .rename-target.*alternative_name_a",
        ),
        (
            "illegal_mapping_native_rename_target_conflict_2.yaml",
            "Name collision in native regions .rename-target.*alternative_name_a",
        ),
        (
            "illegal_mapping_duplicate_common.yaml",
            "Name collision in common regions.*common_region_1",
        ),
        (
            "illegal_mapping_model_only.yaml",
            "one of 'native_regions' and 'common_regions'",
        ),
        (
            "illegal_mapping_constituent_native_missing.yaml",
            "Constituent region\(s\)\n.*\n",
        ),
    ],
)
def test_illegal_mappings(file, error_msg_pattern):
    # This is to test a few different failure conditions

    with pytest.raises(pydantic.ValidationError, match=f"{error_msg_pattern}.*{file}"):
        RegionAggregationMapping.from_file(TEST_FOLDER_REGION_AGGREGATION / file)


def test_illegal_additional_attribute():
    with pytest.raises(
        pydantic.ValidationError, match="Extra inputs are not permitted"
    ):
        RegionAggregationMapping.from_file(
            TEST_FOLDER_REGION_AGGREGATION / "illegal_mapping_illegal_attribute.yaml"
        )


def test_mapping_parsing_error():
    with pytest.raises(ValueError, match="string indices must be integers"):
        RegionAggregationMapping.from_file(
            TEST_FOLDER_REGION_AGGREGATION / "illegal_mapping_invalid_format_dict.yaml"
        )


@pytest.mark.parametrize(
    "region_processor_path",
    [
        TEST_FOLDER_REGION_PROCESSING / "regionprocessor_working",
        (TEST_FOLDER_REGION_PROCESSING / "regionprocessor_working").relative_to(
            Path.cwd()
        ),
    ],
)
def test_region_processor_working(region_processor_path, simple_definition):
    obs = RegionProcessor.from_directory(region_processor_path, simple_definition)
    exp_data = [
        {
            "model": ["model_a"],
            "file": (
                TEST_FOLDER_REGION_PROCESSING / "regionprocessor_working/mapping_1.yml"
            ).relative_to(Path.cwd()),
            "native_regions": [
                {"name": "World", "rename": None},
            ],
            "common_regions": [],
            "exclude_regions": [],
        },
        {
            "model": ["model_b"],
            "file": (
                TEST_FOLDER_REGION_PROCESSING / "regionprocessor_working/mapping_2.yaml"
            ).relative_to(Path.cwd()),
            "native_regions": [],
            "common_regions": [
                {
                    "name": "World",
                    "constituent_regions": ["region_a", "region_b"],
                }
            ],
            "exclude_regions": ["region_c"],
        },
    ]
    exp_models = {value["model"][0] for value in exp_data}
    exp_dict = {value["model"][0]: value for value in exp_data}

    assert exp_models == set(obs.mappings.keys())
    assert all(exp_dict[m] == obs.mappings[m].model_dump() for m in exp_models)


def test_region_processor_not_defined(simple_definition):
    # Test a RegionProcessor with regions that are not defined in the DataStructureDefinition
    error_msg = (
        "mappings.model_(a|b).*\n"
        ".*\n.*region_a.*\n.*mapping_(1|2).yaml\n.*region_not_defined.*\n"
        "mappings.model_(a|b).*\n"
        ".*\n.*region_a.*\n.*mapping_(1|2).yaml\n.*region_not_defined"
    )

    with pytest.raises(ValueError, match=error_msg):
        RegionProcessor.from_directory(
            TEST_FOLDER_REGION_PROCESSING / "regionprocessor_not_defined",
            simple_definition,
        )


def test_region_processor_duplicate_model_mapping(simple_definition):
    with pytest.RaisesGroup(
        ValueError, match="Found errors in RegionProcessor"
    ) as excinfo:
        RegionProcessor.from_directory(
            TEST_FOLDER_REGION_PROCESSING / "regionprocessor_duplicate",
            simple_definition,
        )
    match = ".*model_a.*mapping_(1|2).yaml.*mapping_(1|2).yaml"
    assert excinfo.group_contains(ValueError, match=match)


def test_region_processor_wrong_args():
    # Test if pydantic correctly type checks the input of RegionProcessor.from_directory

    # Test with an integer
    with pytest.raises(pydantic.ValidationError, match=".*path\n.*not a valid path.*"):
        RegionProcessor.from_directory(path=123)

    # Test with a file, a path pointing to a directory is required
    with pytest.raises(
        pydantic.ValidationError,
        match=".*path\n.*does not point to a directory.*",
    ):
        RegionProcessor.from_directory(
            path=TEST_FOLDER_REGION_PROCESSING
            / "regionprocessor_working"
            / "mapping_1.yml"
        )


def test_region_processor_multiple_wrong_mappings(simple_definition):
    # Read in the entire region_aggregation directory and return **all** errors

    with pytest.raises(ExceptionGroup) as excinfo:
        RegionProcessor.from_directory(
            TEST_FOLDER_REGION_AGGREGATION,
            simple_definition,
        )
    assert len(excinfo.value.exceptions) == 11


def test_region_processor_exclude_model_native_overlap_raises(simple_definition):
    # Test that exclude regions in either native or common regions raise errors

    with pytest.RaisesGroup(
        ValidationError,
        ValidationError,
        match="Found errors in RegionProcessor",
    ) as excinfo:
        RegionProcessor.from_directory(
            TEST_FOLDER_REGION_PROCESSING / "regionprocessor_exclude_region_overlap",
            simple_definition,
        )
    assert excinfo.group_contains(
        ValidationError,
        match=(
            "{'region_a'} can only be present in 'exclude_regions' or 'native_regions'"
        ),
    )
    assert excinfo.group_contains(
        ValidationError,
        match=(
            "{'region_a'} can only be present in 'exclude_regions' or 'common_regions'"
        ),
    )


def test_region_processor_unexpected_region_raises():
    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "region_A", "Primary Energy", "EJ/yr", 1],
                ["model_a", "scen_a", "region_B", "Primary Energy", "EJ/yr", 0.5],
            ],
            columns=IAMC_IDX + [2005],
        )
    )
    with pytest.raises(ValueError, match="Did not find.*'region_B'.*in.*model_a.yaml"):
        process(
            test_df,
            dsd := DataStructureDefinition(
                TEST_DATA_DIR / TEST_DATA_DIR / "region_processing" / "dsd"
            ),
            processor=RegionProcessor.from_directory(
                TEST_FOLDER_REGION_PROCESSING / "regionprocessor_unexpected_region", dsd
            ),
        )


def test_mapping_from_external_repository():
    # This test reads definitions and the mapping for only MESSAGEix-GLOBIOM 2.1-M-R12 # from an external repository only
    try:
        processor = RegionProcessor.from_directory(
            TEST_FOLDER_REGION_PROCESSING / "external_repo_test" / "mappings",
            dsd := DataStructureDefinition(
                TEST_FOLDER_REGION_PROCESSING / "external_repo_test" / "definitions"
            ),
        )
        assert {"REMIND-MAgPIE 3.1-4.6"} == set(processor.mappings.keys())
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_mapping_from_external_repository_missing_regions_raises():
    try:
        with pytest.raises(
            pydantic.ValidationError,
            match="validation errors for RegionProcessor",
        ):
            RegionProcessor.from_directory(
                TEST_FOLDER_REGION_PROCESSING
                / "external_repo_test_missing_region"
                / "mappings",
                dsd := DataStructureDefinition(
                    TEST_FOLDER_REGION_PROCESSING
                    / "external_repo_test_missing_region"
                    / "definitions"
                ),
            )
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_reverse_region_aggregation():
    processor = RegionProcessor.from_directory(
        TEST_FOLDER_REGION_PROCESSING / "complete_processing_list",
        DataStructureDefinition(TEST_FOLDER_REGION_PROCESSING / "dsd"),
    )

    obs = processor.revert(
        IamDataFrame(
            pd.DataFrame(
                [
                    ["m_a", "s_a", "World", "Primary Energy", "EJ/yr", 1, 6.0],
                    ["m_a", "s_a", "region_A", "Primary Energy", "EJ/yr", 0.5, 3],
                    ["m_a", "s_b", "region_B", "Primary Energy", "EJ/yr", 2, 7],
                    ["m_c", "s_a", "World", "Primary Energy", "EJ/yr", 1, 2],
                ],
                columns=IAMC_IDX + [2005, 2010],
            )
        )
    )
    exp = IamDataFrame(
        pd.DataFrame(
            [
                ["m_a", "s_a", "region_a", "Primary Energy", "EJ/yr", 0.5, 3],
                ["m_a", "s_b", "region_B", "Primary Energy", "EJ/yr", 2, 7],
            ],
            columns=IAMC_IDX + [2005, 2010],
        ),
    )
    assert_iamframe_equal(obs, exp)


def test_model_mapping_from_excel():
    excel_file = TEST_DATA_DIR / "model_registration" / "excel_model_registration.xlsx"
    obs = RegionAggregationMapping.from_file(excel_file)
    exp = RegionAggregationMapping(
        model=["Model 1.1"],
        file=excel_file,
        native_regions=[
            NativeRegion(name="Region 1", rename="Model 1.1|Region 1"),
            NativeRegion(name="Region 2"),
            NativeRegion(name="Region 3"),
            NativeRegion(name="Region 4"),
            NativeRegion(name="Region 5"),
            NativeRegion(name="Region 6"),
            NativeRegion(name="Region 7"),
        ],
        common_regions=[
            CommonRegion(
                name="World",
                constituent_regions=[
                    "Region 1",
                    "Region 2",
                    "Region 3",
                    "Region 4",
                    "Region 5",
                    "Region 6",
                    "Region 7",
                ],
            ),
            CommonRegion(
                name="Common Region 1", constituent_regions=["Region 1", "Region 2"]
            ),
            CommonRegion(name="Asia (R5)", constituent_regions=["Region 1"]),
            CommonRegion(
                name="Latin America (R5)", constituent_regions=["Region 6", "Region 7"]
            ),
            CommonRegion(
                name="Middle East & Africa (R5)", constituent_regions=["Region 5"]
            ),
            CommonRegion(
                name="OECD & EU (R5)", constituent_regions=["Region 2", "Region 3"]
            ),
            CommonRegion(
                name="Reforming Economies (R5)", constituent_regions=["Region 4"]
            ),
        ],
    )

    assert obs == exp


def test_model_mapping_from_excel_to_yaml(tmp_path):
    excel_file = TEST_DATA_DIR / "model_registration" / "excel_model_registration.xlsx"
    # Create a yaml mapping from an excel mapping
    RegionAggregationMapping.from_file(excel_file).to_yaml(tmp_path / "mapping.yaml")

    obs = RegionAggregationMapping.from_file(tmp_path / "mapping.yaml")

    exp = RegionAggregationMapping.from_file(
        TEST_DATA_DIR / "model_registration" / "excel_mapping_reference.yaml"
    )
    assert obs == exp
