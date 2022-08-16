import click
from pathlib import Path

from nomenclature.testing import assert_valid_yaml, assert_valid_structure

cli = click.Group()


@cli.command("validate-yaml")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def cli_valid_yaml(path: Path):
    """Assert that all yaml files in `path` are syntactically valid."""
    assert_valid_yaml(path)


@cli.command("validate-project")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--mappings", type=str, default="mappings")
@click.option("--definitions", type=str, default="definitions")
def cli_valid_project(path: Path, mappings: str, definitions: str):
    """Assert that `path` is a valid project nomenclature

    This test includes three steps:

    1. Test that all yaml files in `definitions/` and `mappings/` can be correctly read
       as yaml files. This is a formal check for yaml syntax only.
    2. Test that all files in `definitions/` can be correctly parsed as a
       :class:`DataStructureDefinition` object comprised of individual codelists.
    3. Test that all model mappings in `mappings/` can be correctly parsed as a
       :class:`RegionProcessor` object. This includes a check that all regions mentioned
       in a model mapping are defined in the region codelist.

    Example
    -------
    $ nomenclature validate-project . --mappings map --definitions def

    """
    assert_valid_yaml(path)
    assert_valid_structure(path, mappings, definitions)
