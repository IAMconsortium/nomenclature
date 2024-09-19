import logging
from importlib.metadata import version
from pathlib import Path

import yaml

from nomenclature.cli import cli  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.core import process  # noqa
from nomenclature.countries import countries  # noqa
from nomenclature.nuts import nuts  # noqa
from nomenclature.definition import SPECIAL_CODELIST, DataStructureDefinition  # noqa
from nomenclature.processor import RegionAggregationMapping  # noqa
from nomenclature.processor import RegionProcessor, RequiredDataValidator  # noqa

# set up logging
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

__version__ = version("nomenclature-iamc")


def create_yaml_from_xlsx(source, target, sheet_name, col, attrs=None):
    """Parses an xlsx file with a codelist and writes a yaml file

    Parameters
    ----------
    source : str, path, file-like object
        Path to xlsx file with definitions (codelists).
    target : str, path, file-like object
        Path to save the parsed definitions as yaml file.
    sheet_name : str
        Sheet name of `source`.
    col : str
        Column from `sheet_name` to use as codes.
    attrs : list, optional
        Columns from `sheet_name` to use as attributes.
    """
    if attrs is None:
        attrs = []
    SPECIAL_CODELIST.get(col.lower(), CodeList).read_excel(
        name="", source=source, sheet_name=sheet_name, col=col, attrs=attrs
    ).to_yaml(target)


def parse_model_registration(
    model_registration_file: str | Path, output_directory: str | Path = Path(".")
) -> None:
    """Parses a model registration file and writes the definitions & mapping yaml files

    Parameters
    ----------
    model_registration_file : str, path, file-like object
        Path to xlsx model registration file.
    output_directory : str, path, file-like object
        Directory where the model mapping and region file will be saved;
        defaults to current working directory
    """
    if not isinstance(output_directory, Path):
        output_directory = Path(output_directory)

    region_aggregregation_mapping = RegionAggregationMapping.from_file(
        model_registration_file
    )
    file_model_name = "".join(
        x if (x.isalnum() or x in "._- ") else "_"
        for x in region_aggregregation_mapping.model[0]
    )
    region_aggregregation_mapping.to_yaml(
        output_directory / f"{file_model_name}_mapping.yaml"
    )
    if native_regions := [
        {
            region_aggregregation_mapping.model[
                0
            ]: region_aggregregation_mapping.upload_native_regions
        }
    ]:
        with open(
            (output_directory / f"{file_model_name}_regions.yaml"),
            "w",
            encoding="utf-8",
        ) as file:
            yaml.dump(native_regions, file)
