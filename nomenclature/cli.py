import ast
from pathlib import Path
from typing import List, Optional

import click

from nomenclature.testing import assert_valid_structure, assert_valid_yaml

cli = click.Group()


class PythonLiteralOption(click.Option):
    def type_cast_value(self, ctx, value):
        if value is None:
            return None
        try:
            return ast.literal_eval(value)
        except Exception:
            raise click.BadParameter(value)


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
    cls=PythonLiteralOption,
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
