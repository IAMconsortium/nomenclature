import importlib.util
import sys
from pathlib import Path
from typing_extensions import Annotated

import pandas as pd
import typer
import yaml
from pyam import IamDataFrame

from nomenclature import __version__
from nomenclature.codelist import CodeList, VariableCodeList
from nomenclature.definition import SPECIAL_CODELIST, DataStructureDefinition
from nomenclature.processor import RegionAggregationMapping, RegionProcessor
from nomenclature.testing import assert_valid_structure, assert_valid_yaml

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"nomenclature, version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    pass


# ---------------------------------------------------------
# validate-yaml
# ---------------------------------------------------------
@app.command()
def validate_yaml(
    path: Annotated[
        Path,
        typer.Argument(
            ..., exists=True, help="Directory containing YAML files to validate"
        ),
    ],
):
    """Validate YAML syntax in all files within a directory.

    Performs a formal check that all YAML files can be parsed without syntax errors.
    This does not validate the content, only the YAML structure.
    """
    assert_valid_yaml(path)


# ---------------------------------------------------------
# validate-project
# ---------------------------------------------------------
@app.command()
def validate_project(
    path: Annotated[
        Path, typer.Argument(..., exists=True, help="Project directory to validate")
    ],
    definitions: Annotated[
        str, typer.Option(help="Name of definitions folder")
    ] = "definitions",
    mappings: Annotated[
        str | None, typer.Option(help="Name of mappings folder")
    ] = None,
    required_data: Annotated[
        str | None, typer.Option(help="Name of required data folder")
    ] = None,
    validate_data: Annotated[
        str | None, typer.Option(help="Name of data validation folder")
    ] = None,
    dimensions: Annotated[
        list[str] | None,
        typer.Option("--dimension", help="Dimensions to check (defaults to all)"),
    ] = None,
):
    """Validate a nomenclature project directory structure and content.

    Performs comprehensive validation including:
    - YAML syntax validation for all files
    - Parsing of codelists in the definitions folder
    - Validation of model mappings against region codelists
    - Consistency checks for required-data and data-validation criteria

    Example:
      $ nomenclature validate-project . --definitions def --mappings map
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
    input_data_file: Annotated[
        Path,
        typer.Argument(..., exists=True, help="Input IAMC data file (.xlsx or .csv)"),
    ],
    workflow_directory: Annotated[
        Path,
        typer.Option(
            exists=True, help="Workflow directory with codelists and mappings"
        ),
    ] = Path.cwd(),
    definitions: Annotated[
        str, typer.Option(help="Definitions folder name")
    ] = "definitions",
    mappings: Annotated[str, typer.Option(help="Mappings folder name")] = "mappings",
    processed_data: Annotated[
        Path | None, typer.Option(help="Output file for processed data")
    ] = (Path.cwd() / "results.xlsx"),
    differences: Annotated[
        Path | None, typer.Option(help="Output file for aggregation differences")
    ] = None,
):
    """Perform region aggregation and validate against original data.

    Applies model-specific region mappings to aggregate native regions into common
    regions (e.g., national data to R5 regions). Compares aggregated results with
    any pre-aggregated data in the input file and reports differences.

    Useful for quality control of model-reported regional data.

    Example:
      $ nomenclature check-region-aggregation input.xlsx --processed-data results.xlsx
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
    path: Annotated[Path, typer.Argument(..., exists=True, help="Project directory")],
    target: Annotated[Path, typer.Argument(..., help="Output Excel file path")],
):
    """Export project codelists to Excel for review or editing.

    Creates an Excel workbook with separate sheets for each dimension (variable,
    region, etc.) containing all codelist definitions and attributes.

    Example:
      $ nomenclature export-definitions . codelists.xlsx
    """
    DataStructureDefinition(path / "definitions").to_excel(target)


# ---------------------------------------------------------
# list-missing-variables
# ---------------------------------------------------------
@app.command()
def list_missing_variables(
    data: Annotated[
        Path, typer.Argument(..., exists=True, help="IAMC data file (.xlsx or .csv)")
    ],
    workflow_directory: Annotated[
        Path, typer.Option(help="Workflow directory with variable codelist")
    ] = Path.cwd(),
    target_file: Annotated[
        str | None, typer.Option(help="Target YAML file for missing variables")
    ] = None,
):
    """Identify and optionally export variables not in the codelist.

    Scans an IAMC data file for variables that are not defined in the project's
    variable codelist. Can generate a template YAML file with the missing variables
    for review and addition to the codelist.

    Example:
      $ nomenclature list-missing-variables input.xlsx --target-file new_vars.yaml
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
    input_file: Annotated[
        Path, typer.Argument(..., exists=True, help="Input IAMC data file")
    ],
    workflow_file: Annotated[
        Path, typer.Option(exists=True, help="Python workflow file")
    ] = (Path.cwd() / "workflow.py"),
    workflow_function: Annotated[
        str, typer.Option(help="Function name in workflow file")
    ] = "main",
    output_file: Annotated[
        Path | None, typer.Option(help="Output file for processed data")
    ] = None,
):
    """Execute a custom Python workflow on IAMC data.

    Loads a function from a Python file and applies it to process scenario data.
    The workflow function should accept an IamDataFrame and return an IamDataFrame.
    Useful for project-specific data transformations and validation.

    Example:
      $ nomenclature run-workflow input.xlsx --output-file output.xlsx
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
    input_file: Annotated[
        Path, typer.Argument(..., exists=True, help="IAMC data file to validate")
    ],
    definitions: Annotated[
        Path, typer.Option(exists=True, help="Definitions folder with codelists")
    ] = Path("definitions"),
    dimensions: Annotated[
        list[str] | None,
        typer.Option("--dimension", help="Dimensions to validate (defaults to all)"),
    ] = None,
):
    """Validate scenario data against project codelists.

    Verifies that specified dimensions (variables, regions, scenarios, etc.) in an IAMC
    data file are defined in the project codelists.

    Example:
      $ nomenclature validate-scenarios input.xlsx --definitions defs
    """
    DataStructureDefinition(definitions, dimensions).validate(IamDataFrame(input_file))


@app.command()
def convert_xlsx_codelist_to_yaml(
    source: Annotated[
        Path, typer.Argument(..., exists=True, help="Excel file with codelist")
    ],
    target: Annotated[Path, typer.Argument(..., help="Output YAML file path")],
    sheet_name: Annotated[str, typer.Argument(..., help="Sheet name in Excel file")],
    col: Annotated[str, typer.Argument(..., help="Column to use as codes")],
    attrs: Annotated[
        list[str] | None, typer.Option(help="Columns to use as attributes")
    ] = None,
):
    """Convert Excel-based codelist to YAML format.

    Reads a codelist from a specified Excel sheet and column, preserving any
    attributes, and exports it as a structured YAML file compatible with the
    nomenclature definitions format.

    Example:
      $ nomenclature convert-xlsx-codelist-to-yaml input.xlsx output.yaml sheet1 variable
    """
    if attrs is None:
        attrs = []
    SPECIAL_CODELIST.get(col.lower(), CodeList).read_excel(
        name="", source=source, sheet_name=sheet_name, col=col, attrs=attrs
    ).to_yaml(target)


@app.command()
def parse_model_registration(
    model_registration_file: Annotated[
        Path, typer.Argument(..., exists=True, help="Excel model registration file")
    ],
    definition_path: Annotated[
        Path, typer.Option(exists=True, help="Region definitions output folder")
    ] = (Path.cwd() / "definitions" / "region"),
    mappings_path: Annotated[
        Path, typer.Option(exists=True, help="Model mappings output folder")
    ] = Path.cwd() / "mappings",
) -> None:
    """Parse model registration spreadsheet and generate YAML files.

    Reads a standardized Excel model registration file containing native region
    definitions and common region mappings. Generates two sets of YAML files:
    - Region definitions with optional country mappings
    - Model-specific region aggregation mappings

    Supports R5 region conventions with automatic World region generation.

    Example:
      $ nomenclature parse-model-registration registration.xlsx
    """

    # Parse Common-Region-Mapping
    region_aggregation_mapping = RegionAggregationMapping.from_file(
        model_registration_file
    )
    file_model_name = "".join(
        x if (x.isalnum() or x in "._- ") else "_"
        for x in region_aggregation_mapping.model[0]
    ).replace(" ", "_")
    region_aggregation_mapping.to_yaml(
        mappings_path / f"{file_model_name}.yaml",
    )
    # Parse Region-Country-Mapping
    if "Region-Country-Mapping" in pd.ExcelFile(model_registration_file).sheet_names:
        native = "Native region (as reported by the model)"
        constituents = "Country name"
        region_country_mapping = pd.read_excel(
            model_registration_file,
            sheet_name="Region-Country-Mapping",
            header=2,
            usecols=[native, constituents],
        )
        region_country_mapping = (
            region_country_mapping.dropna().groupby(native)[constituents].apply(list)
        )
    else:
        print(
            "No 'Region-Country-Mapping' sheet found in model registration spreadsheet."
        )
        region_country_mapping = pd.DataFrame()
    if native_regions := [
        {
            region_aggregation_mapping.model[
                0
            ]: region_aggregation_mapping.upload_native_regions
        }
    ]:
        if not region_country_mapping.empty:

            def construct_region_mapping(region):
                countries = region_country_mapping.get(region.name, None)
                if countries:
                    return {region.target_native_region: {"countries": countries}}
                return region.target_native_region

            native_regions = [
                construct_region_mapping(region)
                for region in region_aggregation_mapping.native_regions
            ]
            native_regions = [{region_aggregation_mapping.model[0]: native_regions}]
        with open(
            definition_path / f"{file_model_name}.yaml",
            "w",
            encoding="utf-8",
        ) as file:
            yaml.dump(native_regions, file, allow_unicode=True)
