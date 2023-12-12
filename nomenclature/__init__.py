import logging
from importlib.metadata import version
from pathlib import Path

import yaml
from setuptools_scm import get_version

from nomenclature.cli import cli  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.core import process  # noqa
from nomenclature.countries import countries  # noqa
from nomenclature.definition import SPECIAL_CODELIST, DataStructureDefinition  # noqa
from nomenclature.processor import RegionAggregationMapping  # noqa
from nomenclature.processor import RegionProcessor, RequiredDataValidator

# set up logging
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# get version number either from git (preferred) or metadata
try:
    __version__ = get_version(Path(__file__).parents[1])
except LookupError:
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


def parse_model_registration(model_registration_file, output_file_name):
    """Parses a model registration file and writes the definitions & mapping yaml files

    Parameters
    ----------
    source : str, path, file-like object
        Path to xlsx model registration file.
    file_name : str
        Model-identifier part of the yaml file names.
    """
    RegionAggregationMapping.from_file(model_registration_file).to_yaml(
        output_file_name
    )
