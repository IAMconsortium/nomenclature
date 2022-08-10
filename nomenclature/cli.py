import click
from pathlib import Path

from nomenclature.testing import assert_valid_yaml, assert_valid_structure

cli = click.Group()


@cli.command("validate-yaml")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def cli_valid_yaml(path: Path):
    """Assert that all yaml files in `path` can be parsed without errors"""
    assert_valid_yaml(path)


@cli.command("validate-project")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
#@click.argument("dimensions", nargs=-1)
@click.option('--dimensions', help='Optional list of dimensions', type=str)
def cli_valid_project(path: Path, dimensions):
    """Assert that `path` is a valid project nomenclature"""
    list_dimensions = list(dimensions.split(","))
    assert_valid_yaml(path)
    assert_valid_structure(path, list_dimensions)
