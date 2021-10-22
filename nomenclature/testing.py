import yaml
import logging
from pathlib import Path

import click

logger = logging.getLogger(__name__)


@click.group(chain=True)
def cli():
    pass


@cli.command('assert_valid_yaml')
@click.argument("path", type=click.Path(exists=True))
def assert_valid_yaml(path):
    """Assert that all yaml files in `path` can be parsed without errors"""

    # iterate over the yaml files in all sub-folders and try loading each
    error = False
    for file in Path(path).glob("**/*.yaml"):
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
