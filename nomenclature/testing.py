import yaml
import logging
from pathlib import Path

import click

import nomenclature

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.argument(
    "path", type=click.Path(exists=True, path_type=Path, file_okay=False, dir_okay=True)
)
def cli(path: Path):
    assert_valid_yaml(path)
    check_valid_structure(path)


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


def check_valid_structure(path: Path):
    """Check that "definition" folder in `path` exists and can be initialized without errors"""
    nomenclature.DataStructureDefinition(path / "definitions")
