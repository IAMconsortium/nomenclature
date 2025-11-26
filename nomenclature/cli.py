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
    """Assert that `path` is a valid project nomenclature."""
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
    """Perform region processing and compare aggregated and original data."""
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
    """Create a list of variables that are not part of the variable codelist."""
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
    """Run a given input file through a workflow function defined in workflow.py."""
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
    """Validate a scenario file against the codelists of a project."""
    DataStructureDefinition(definitions, dimensions).validate(IamDataFrame(input_file))
