import click
import ast
from pathlib import Path
from typing import List, Optional

from nomenclature.testing import assert_valid_yaml, assert_valid_structure

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
    "--dimensions",
    help="Optional list of dimensions",
    cls=PythonLiteralOption,
    default=None,
)
@click.option(
    "--mappings", help="Optional name for mappings folder", type=str, default=None
)
@click.option(
    "--definitions",
    help="Optional name for definitions folder",
    type=str,
    default="definitions",
)
def cli_valid_project(
    path: Path,
    dimensions: Optional[List[str]],
    mappings: Optional[str],
    definitions: str,
):
    """Assert that `path` is a valid project nomenclature

    Parameters
    ----------
    path : Path
        directory path to the file of interest
    dimensions : List[str], optional
        List of dimensions to be checked, default to None which implies that all
        directories in `dimensions` will be checked
    mappings : str, optional
        Name for the mappings folder, defaults to None which implies that if the
        `mappings` directory is not found, there are no mappings to check
    definitions : str, optional
        Name for the definitions folder, defaults to "definitions"

    Example
    -------
    $ nomenclature validate-project .
                        --dimensions "['<folder1>', '<folder2>', '<folder3>']"
                        --mappings <map-folder> --definitions <def-folder>

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
    assert_valid_structure(path, dimensions, mappings, definitions)
