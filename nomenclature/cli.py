from pathlib import Path
from typing import List, Optional

import click

from pyam import IamDataFrame
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import RegionProcessor
from nomenclature.testing import assert_valid_structure, assert_valid_yaml

cli = click.Group()


@cli.command("validate-yaml")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def cli_valid_yaml(path: Path):
    """Assert that all yaml files in `path` are syntactically valid."""
    assert_valid_yaml(path)


@cli.command("validate-project")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--definitions",
    help="Optional name for definitions folder",
    type=str,
    default="definitions",
)
@click.option(
    "--mappings", help="Optional name for mappings folder", type=str, default=None
)
@click.option(
    "--required-data",
    help="Optional name for required data folder",
    type=str,
    default=None,
)
@click.option(
    "--dimensions",
    help="Optional list of dimensions",
    type=str,
    multiple=True,
    default=None,
)
def cli_valid_project(
    path: Path,
    definitions: str,
    mappings: Optional[str],
    required_data: Optional[str],
    dimensions: Optional[List[str]],
):
    """Assert that `path` is a valid project nomenclature

    Parameters
    ----------
    path : Path
        Project directory to be validated
    definitions : str, optional
        Name of the definitions folder, defaults to "definitions"
    mappings : str, optional
        Name of the mappings folder, defaults to "mappings" (if this folder exists)
    required_data: str, optional
        Name of the required data folder, default to "required_data" (if folder exists)
    dimensions : List[str], optional
        Dimensions to be checked, defaults to all sub-folders of `definitions`

    Example
    -------
    $ nomenclature validate-project .
                        --definitions <def-folder> --mappings <map-folder>
                        --dimensions "['<folder1>', '<folder2>', '<folder3>']"


    Note
    ----
    This test includes three steps:

    1. Test that all yaml files in `definitions/` and `mappings/` can be correctly read
       as yaml files. This is a formal check for yaml syntax only.
    2. Test that all files in `definitions/` can be correctly parsed as a
       :class:`DataStructureDefinition` object comprised of individual codelists.
    3. Test that all model mappings in `mappings/` can be correctly parsed as a
       :class:`RegionProcessor` object. This includes a check that all regions mentioned
       in a model mapping are defined in the region codelist.

    """
    assert_valid_yaml(path)
    assert_valid_structure(path, definitions, mappings, required_data, dimensions)


@cli.command("check-region-aggregation")
@click.argument("input_data_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-w",
    "--workflow-directory",
    type=click.Path(exists=True, path_type=Path),
    default=".",
)
@click.option("-d", "--definitions", type=str, default="definitions")
@click.option("-m", "--mappings", type=str, default="mappings")
@click.option(
    "--processed-data", type=click.Path(path_type=Path), default="results.xlsx"
)
@click.option("--differences", type=click.Path(path_type=Path), default=None)
def check_region_aggregation(
    input_data_file: Path,
    workflow_directory: Path,
    definitions: str,
    mappings: str,
    processed_data: Optional[Path],
    differences: Optional[Path],
):
    """Perform region processing and compare aggregated and original data

    Parameters
    ----------
    input_data_file : Path
        Location of input data
    workflow_directory : Path
        Location of the workflow directory containing codelists and model mappings, by
        default .
    definitions : str
        Definitions folder inside workflow_directory, by default "definitions"
    mappings : str
        Model mapping folder inside workflow_directory, by default "mappings"
    processed_data : Optional[Path]
        If given, exports the results from region processing to a file called
        `processed_data`, by default "results.xlsx"
    differences : Optional[Path]
        If given, exports the differences between aggregated and model native data to a
        file called `differences`, by default None

    Example
    -------

    This example runs the region processing for input data located in
    ``input_data.xlsx`` based on a workflow directory called ``workflow_directory``. The
    results of the aggregation will be exported to results.xlsx and the differences to
    differences.xlsx.

    $ nomenclature check-region-processing input_data.xlsx -w workflow_directory
                        --processed_data results.xlsx --differences differences.xlsx

    """
    results_df, differences_df = RegionProcessor.from_directory(
        workflow_directory / mappings,
        DataStructureDefinition(workflow_directory / definitions),
    ).check_region_aggregation(IamDataFrame(input_data_file))
    if processed_data:
        results_df.to_excel(processed_data)
    if differences:
        differences_df.reset_index().to_excel(differences, index=False)
