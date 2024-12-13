from pathlib import Path
import importlib.util
import sys

import click

from pyam import IamDataFrame
from nomenclature.definition import DataStructureDefinition
from nomenclature.codelist import VariableCodeList
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
    "--validate_data",
    help="Optional name for validation folder",
    type=str,
    default=None,
)
@click.option(
    "--dimension",
    "dimensions",
    help="Optional list of dimensions",
    type=str,
    multiple=True,
    default=None,
)
def cli_valid_project(
    path: Path,
    definitions: str,
    mappings: str | None,
    required_data: str | None,
    validate_data: str | None,
    dimensions: list[str] | None,
):
    """Assert that `path` is a valid project nomenclature

    Parameters
    ----------
    path : Path
        Project directory to be validated
    definitions : str, optional
        Name of 'definitions' folder, defaults to "definitions"
    mappings : str, optional
        Name of 'mappings' folder, defaults to "mappings"
    required_data: str, optional
        Name of folder for 'required data' criteria, default to "required_data"
    validate_data: str, optional
        Name of folder for data validation criteria, default to "validate_data"
    dimensions : list[str], optional
        Dimensions to be checked, defaults to all sub-folders of `definitions`

    Example
    -------
    $ nomenclature validate-project .
                        --definitions <def-folder> --mappings <map-folder>
                        --dimension <folder1>
                        --dimension <folder2>
                        --dimension <folder3>

    Note
    ----
    This test includes three steps:

    1. Test that all yaml files in `definitions` and `mappings` can be correctly parsed
       as yaml files. This is a formal check for yaml syntax only.
    2. Test that all files in `definitions` can be correctly parsed as a
       :class:`DataStructureDefinition` object comprised of individual codelists.
    3. Test that all model mappings in `mappings` can be correctly parsed as a
       :class:`RegionProcessor` object. This includes a check that all regions mentioned
       in a model mapping are defined in the region codelist.
    4. Test that all required-data and data-validation files can be parsed correctly
       and are consistent with the `definitions`.

    """
    assert_valid_yaml(path)
    assert_valid_structure(
        path, definitions, mappings, required_data, validate_data, dimensions
    )


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
    processed_data: Path | None,
    differences: Path | None,
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
    processed_data : Path, optional
        If given, exports the results from region processing to a file called
        `processed_data`, by default "results.xlsx"
    differences : Path, optional
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


@cli.command("export-definitions")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.argument("target", type=click.Path(path_type=Path))
def cli_export_definitions_to_excel(
    path: Path,
    target: Path,
):
    """Assert that `path` is a valid project nomenclature

    Parameters
    ----------
    path : Path
        Project directory to be exported
    target : Path
        Path and file name for the exported file
    """
    DataStructureDefinition(path / "definitions").to_excel(target)


@cli.command("list-missing-variables")
@click.argument("data", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--workflow-directory",
    default=lambda: Path.cwd(),
    type=Path,
)
@click.option("--target-file", type=str)
def cli_list_missing_variables(
    data: Path, workflow_directory: Path, target_file: Path | None
):
    """Create a list of variables that are not part of the variable codelist

    Parameters
    ----------
    data : Path
        path to the IAMC data file, can be .xlsx or .csv
    workflow_directory : Path, default current working directory
        Path to the workflow directory that contains the variable codelist
    target_file : Path | None
        Name of the target variable definition file, optional, defaults to
        'variables.yaml'
    Example
    -------

    The following command will add all the missing variables to the file
    new_variables.yaml located in my_workflow/definitions/variable:

    $ nomenclature list-missing-variables input_data.xlsx --workflow-directory
                        my_workflow

    """
    codelist_path = workflow_directory / "definitions" / "variable"
    target_file = target_file if target_file is None else codelist_path / target_file
    VariableCodeList.from_directory(
        "variable",
        codelist_path,
    ).list_missing_variables(IamDataFrame(data), target_file)


@cli.command("run-workflow")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--workflow-file",
    default=lambda: Path.cwd() / "workflow.py",
    type=click.Path(exists=True, path_type=Path),
)
@click.option("--workflow-function", default="main")
@click.option("--output-file", type=click.Path())
def cli_run_workflow(
    input_file: Path,
    workflow_file: Path,
    workflow_function: str,
    output_file: Path | None,
):
    """Run a given input file through a workflow function defined in a workflow.py

    Parameters
    ----------
    input_file : Path
        Input data file, must be IAMC format, .xlsx or .csv
    workflow_file : Path
            Path to the workflow file,
            default: current working directory / "workflow.py"
    workflow_function : str
        Name of the workflow function inside the workflow file, default: main
    output_file : Path | None
        Path to the output file where the processing results is saved, nothing
        is saved if None is given, default: None

    Raises
    ------
    ValueError
        If the workflow_file does not have the specified workflow_function
    """

    module_name = workflow_file.stem
    spec = importlib.util.spec_from_file_location(module_name, workflow_file)
    workflow = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = workflow
    spec.loader.exec_module(workflow)

    if not hasattr(workflow, workflow_function):
        raise ValueError(f"{workflow} does not have a function `{workflow_function}`")

    df = getattr(workflow, workflow_function)(IamDataFrame(input_file))
    if output_file is not None:
        df.to_excel(output_file)


@cli.command("validate-scenarios")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--definitions",
    help="Optional name for definitions folder",
    type=click.Path(exists=True, path_type=Path),
    default="definitions",
)
@click.option(
    "--dimension",
    "dimensions",
    help="Optional list of dimensions",
    type=str,
    multiple=True,
    default=None,
)
def cli_validate_scenarios(input_file: Path, definitions: Path, dimensions: list[str]):
    """Validate a scenario file against the codelists of a project

    Example
    -------
    $ nomenclature validate-scenarios <input-file>
                        --definitions <def-folder>
                        --dimension <folder1>
                        --dimension <folder2>
                        --dimension <folder3>

    Parameters
    ----------
    input_file : Path
        Input data file, must be IAMC format, .xlsx or .csv
    definitions : Path
        Definitions folder with codelists, by default "definitions"
    dimensions : list[str], optional
        Dimensions to be checked, defaults to all sub-folders of `definitions`

    Raises
    ------
    ValueError
        If input_file validation fails against specified codelist(s).
    """
    DataStructureDefinition(definitions, dimensions).validate(IamDataFrame(input_file))
