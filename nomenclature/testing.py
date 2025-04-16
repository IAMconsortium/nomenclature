import logging
from pathlib import Path

import yaml

from nomenclature.definition import DataStructureDefinition
from nomenclature.processor import (
    DataValidator,
    RegionProcessor,
    RequiredDataValidator,
    Processor,
)
from nomenclature.error import ErrorCollector

logger = logging.getLogger(__name__)

ILLEGAL_CHARS = ["\u202f"]


def assert_valid_yaml(path: Path):
    """Assert that all yaml files in `path` can be parsed without errors"""

    special_characters = ""

    # iterate over the yaml files in all sub-folders and try loading each
    error = False
    for file in (f for f in path.glob("**/*") if f.suffix in {".yaml", ".yml"}):
        try:
            with open(file, "r", encoding="utf-8") as stream:
                yaml.safe_load(stream)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
            error = True
            logger.error(f"Error parsing file {e}")

        with open(file, "r", encoding="utf-8") as all_lines:
            # check if any special character is found in the file
            for index, line in enumerate(all_lines.readlines()):
                for col, char in enumerate(line):
                    if char in ILLEGAL_CHARS:
                        special_characters += (
                            f"\n - {file.name}, line {index + 1}, col {col + 1}. "
                        )

    if special_characters:
        raise AssertionError(f"Unexpected special character(s): {special_characters}")

    # test fails if any file cannot be parsed, raise error with list of these files
    if error:
        raise AssertionError(
            "Parsing the yaml files failed. Please check the log for details."
        )


def _check_mappings(
    path: Path,
    dsd: DataStructureDefinition,
    mappings: str | None = None,
) -> None:
    if mappings is None:
        if (path / "mappings").is_dir():
            RegionProcessor.from_directory(path / "mappings", dsd)
    elif (path / mappings).is_dir():
        RegionProcessor.from_directory(path / mappings, dsd)
    else:
        raise FileNotFoundError(f"Mappings directory not found: {path / mappings}")


def _collect_processor_errors(
    path: Path,
    processor: type[RequiredDataValidator] | type[DataValidator],
    dsd: DataStructureDefinition,
) -> None:
    errors = ErrorCollector(description=f"files for '{processor.__name__}' ({path})")
    for file in path.iterdir():
        try:
            processor.from_file(file).validate_with_definition(dsd)
        except ValueError as error:
            errors.append(error)
    if errors:
        raise ValueError(errors)


def _check_processor_directory(
    path: Path,
    dsd: DataStructureDefinition,
    processor: Processor,
    processor_arg: str,
    folder: str | None = None,
) -> None:
    if folder is None:
        if (path / processor_arg).is_dir():
            _collect_processor_errors(path / processor_arg, processor, dsd)
    elif (path / folder).is_dir():
        _collect_processor_errors(path / folder, processor, dsd)
    else:
        raise FileNotFoundError(
            f"Directory for '{processor_arg}' not found at: {path / folder}"
        )


def assert_valid_structure(
    path: Path,
    definitions: str = "definitions",
    mappings: str | None = None,
    required_data: str | None = None,
    validate_data: str | None = None,
    dimensions: list[str] | None = None,
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
    required_data : str, optional
        Name of the folder for required data, defaults to "required_data"
        (if this folder exists)
    validate_data : str, optional
        Name of the folder for data validation criteria, defaults to "validate_data"
        (if this folder exists)
    dimensions : list[str], optional
        Dimensions to be checked, defaults to all sub-folders of `definitions`

    Notes
    -----
    Folder structure of `path`:
        - A `definitions` folder is required and must be a valid
          :class:`DataStructureDefinition`
        - The `definitions` folder must contain sub-folder(s) to validate
        - If a `mappings` folder exists, it must be a valid :class:`RegionProcessor`

    """
    if not (path / definitions).is_dir():
        raise NotADirectoryError(
            f"Definitions directory not found: {path / definitions}"
        )

    dsd = DataStructureDefinition(path / definitions, dimensions)
    _check_mappings(path, dsd, mappings)
    _check_processor_directory(
        path, dsd, RequiredDataValidator, "required_data", required_data
    )
    _check_processor_directory(path, dsd, DataValidator, "validate_data", validate_data)


# Todo: add function which runs `DataStructureDefinition(path).validate(scenario)`
