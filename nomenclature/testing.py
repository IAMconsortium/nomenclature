import yaml
import logging
from pathlib import Path

import click

import nomenclature

logger = logging.getLogger(__name__)

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


def assert_valid_yaml(path: Path):
    """Assert that all yaml files in `path` can be parsed without errors"""

    # iterate over the yaml files in all sub-folders and try loading each
    error = False
    for file in path.glob("**/*.yaml"):
        try:
            with open(file, "r", encoding="utf-8") as stream:
                yaml.safe_load(stream)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
            error = True
            logger.error(f"Error parsing file {e}")

    # test fails if any file cannot be parsed, raise error with list of these files
    if error:
        raise AssertionError(
            "Parsing the yaml files failed. Please check the log for details."
        )


def assert_valid_structure(path: Path):
    """Check that "definitions" folder in `path` exists and
    can be initialized without errors"""
    definition = nomenclature.DataStructureDefinition(path / "definitions")
    if (path / "mappings").is_dir():
        nomenclature.RegionProcessor.from_directory(path / "mappings", definition)


# Todo: add function which runs `DataStrutureDefinition(path).validate(scenario)`
