import importlib.util
import sys
from pathlib import Path
from typing import Annotated, List

import typer
from pyam import IamDataFrame

from nomenclature.codelist import VariableCodeList
from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import RegionProcessor
from nomenclature.testing import assert_valid_structure, assert_valid_yaml

app = typer.Typer(no_args_is_help=True)


# ---------------------------------------------------------
# validate-yaml
# ---------------------------------------------------------
@app.command()
def validate_yaml(path: Annotated[Path, typer.Argument(..., exists=True)]):
    """Assert that all yaml files in `path` are syntactically valid."""
    assert_valid_yaml(path)


# ---------------------------------------------------------
# validate-project
# ---------------------------------------------------------
@app.command()
def validate_project(
    path: Annotated[Path, typer.Argument(..., exists=True)],
    definitions: Annotated[str, typer.Option()] = "definitions",
    mappings: Annotated[str | None, typer.Option()] = None,
    required_data: Annotated[str | None, typer.Option()] = None,
    validate_data: Annotated[str | None, typer.Option()] = None,
    dimensions: Annotated[List[str] | None, typer.Option("--dimension")] = None,
):
    """Assert that `path` is a valid project nomenclature.

    Parameters
    ----------
    path : Path
        Project directory to be validated
    definitions : str, optional
        Name of 'definitions' folder, defaults to "definitions"
    mappings : str, optional
        Name of 'mappings' folder, defaults to "mappings"
    required_data : str, optional
        Name of folder for 'required data' criteria, default to "required_data"
    validate_data : str, optional
        Name of folder for data validation criteria, default to "validate_data"
    dimensions : List[str], optional
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


# ---------------------------------------------------------
# check-region-aggregation
# ---------------------------------------------------------
@app.command()
def check_region_aggregation(
    input_data_file: Annotated[Path, typer.Argument(..., exists=True)],
    workflow_directory: Annotated[Path, typer.Option(exists=True)] = Path.cwd(),
    definitions: Annotated[str, typer.Option()] = "definitions",
    mappings: Annotated[str, typer.Option()] = "mappings",
    processed_data: Annotated[Path | None, typer.Option()] = (
        Path.cwd() / "results.xlsx"
    ),
    differences: Annotated[Path | None, typer.Option()] = None,
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


# ---------------------------------------------------------
# export-definitions
# ---------------------------------------------------------
@app.command("export-definitions")
def export_definitions_to_excel(
    path: Annotated[Path, typer.Argument(..., exists=True)],
    target: Annotated[Path, typer.Argument(...)],
):
    """Export project definitions to Excel."""
    DataStructureDefinition(path / "definitions").to_excel(target)


# ---------------------------------------------------------
# list-missing-variables
# ---------------------------------------------------------
@app.command()
def list_missing_variables(
    data: Annotated[Path, typer.Argument(..., exists=True)],
    workflow_directory: Annotated[Path, typer.Option()] = Path.cwd(),
    target_file: Annotated[str | None, typer.Option()] = None,
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
    final_target = None if target_file is None else codelist_path / target_file

    VariableCodeList.from_directory(
        "variable",
        codelist_path,
    ).list_missing_variables(IamDataFrame(data), final_target)


# ---------------------------------------------------------
# run-workflow
# ---------------------------------------------------------
@app.command()
def run_workflow(
    input_file: Annotated[Path, typer.Argument(..., exists=True)],
    workflow_file: Annotated[Path, typer.Option(exists=True)] = (
        Path.cwd() / "workflow.py"
    ),
    workflow_function: Annotated[str, typer.Option()] = "main",
    output_file: Annotated[Path | None, typer.Option()] = None,
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


# ---------------------------------------------------------
# validate-scenarios
# ---------------------------------------------------------
@app.command()
def validate_scenarios(
    input_file: Annotated[Path, typer.Argument(..., exists=True)],
    definitions: Annotated[Path, typer.Option(exists=True)] = Path("definitions"),
    dimensions: Annotated[List[str] | None, typer.Option("--dimension")] = None,
):
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
