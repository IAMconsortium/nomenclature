import click
import ast
from pathlib import Path
from typing import List

from nomenclature.testing import assert_valid_yaml, assert_valid_structure

cli = click.Group()


class PythonLiteralOption(click.Option):
    def type_cast_value(self, ctx, value):
        try:
            return ast.literal_eval(value)
        except Exception:
            raise click.BadParameter(value)


@cli.command("validate-yaml")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def cli_valid_yaml(path: Path):
    """Assert that all yaml files in `path` can be parsed without errors"""
    assert_valid_yaml(path)


@cli.command("validate-project")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--dimensions",
    help="Optional list of dimensions",
    cls=PythonLiteralOption,
    default="['region', 'variable']",
)
def cli_valid_project(path: Path, dimensions: List[str]):
    """Assert that `path` and `dimensions`(optional) are valid project nomenclatures"""
    assert_valid_yaml(path)
    assert_valid_structure(path, dimensions)
