import yaml
import logging
from pathlib import Path
from typing import List, Optional

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
    path: Path,
    definitions: str = "definitions",
    mappings: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
) -> None:
    """Assert that `path` can be initialized as a :class:`DataStructureDefinition`

    Parameters
    ----------
    path : Path
        Project directory to be validated
    definitions : str, optional
        Name of the definitions folder, defaults to "definitions"
    mappings : str, optional
        Name of the mappings folder, defaults to "mappings" (if this folder exists)
    dimensions : List[str], optional
        Dimensions to be checked, defaults to all sub-folders of `definitions`

    Notes
    -----
    Folder structure of `path`:
        - A `definitions` folder is required and must be a valid
        :class:`DataStructureDefinition`
        - If a `mappings` folder exists, it must be a valid :class:`RegionProcessor`

    """
    if not (path / definitions).is_dir():
        raise NotADirectoryError(
            f"Definitions directory not found: {path / definitions}"
        )
    if dimensions is None:
        dimensions = [x.stem for x in (path / definitions).iterdir() if x.is_dir()]

    definition = nomenclature.DataStructureDefinition(path / definitions, dimensions)
    if mappings is None:
        if (path / "mappings").is_dir():
            nomenclature.RegionProcessor.from_directory(
                path / "mappings"
            ).validate_mappings(definition)
    elif (path / mappings).is_dir():
        nomenclature.RegionProcessor.from_directory(path / mappings).validate_mappings(
            definition
        )
    else:
        raise FileNotFoundError(f"Mappings directory not found: {path / mappings}")


# Todo: add function which runs `DataStructureDefinition(path).validate(scenario)`
