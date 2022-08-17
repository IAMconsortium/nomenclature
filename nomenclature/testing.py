import yaml
import logging
from pathlib import Path

import nomenclature

logger = logging.getLogger(__name__)


def assert_valid_yaml(path: Path):
    """Assert that all yaml files in `path` can be parsed without errors"""

    # iterate over the yaml files in all sub-folders and try loading each
    error = False
    for file in (f for f in path.glob("**/*") if f.suffix in {".yaml", ".yml"}):
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


def assert_valid_structure(
    path: Path, mappings: str = "mappings", definitions: str = "definitions"
) -> None:
    """Assert that `path` can be initialized as a :class:`DataStructureDefinition`

    Parameters
    ----------
    path : Path
        directory path to the file of interest
    mappings : str
        Optionnal non-default name for the mappings folder
    definitions : str
        Optionnal non-default name for the definitions folder

    Notes
    -----
    Folder structure of `path`:
        - A `definitions` folder is required and must be a valid
        :class:`DataStructureDefinition`
        - If a `mappings` folder exists, it must be a valid :class:`RegionProcessor`

    """

    definition = nomenclature.DataStructureDefinition(path / str(definitions))
    if (path / mappings).is_dir():
        nomenclature.RegionProcessor.from_directory(path / mappings).validate_mappings(
            definition
        )
    else:
        if mappings != "mappings":
            raise NotADirectoryError(
                f"Mappings directory not found: {path/ str(mappings)}"
            )


# Todo: add function which runs `DataStrutureDefinition(path).validate(scenario)`
