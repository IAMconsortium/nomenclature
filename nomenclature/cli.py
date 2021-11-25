import click
from pathlib import Path

from nomenclature.testing import assert_valid_yaml, assert_valid_structure

cli = click.Group()


@cli.command("validate-yaml")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def cli_valid_yaml(path: Path):
    assert_valid_yaml(path)


@cli.command("validate-project")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def cli_valid_project(path: Path):
    assert_valid_yaml(path)
    assert_valid_structure(path)

