import logging
from pathlib import Path
from setuptools_scm import get_version
from importlib.metadata import version

from nomenclature.core import process  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.definition import DataStructureDefinition  # noqa
from nomenclature.cli import cli  # noqa
from nomenclature.processor.region import (  # noqa
    RegionProcessor,
    RegionAggregationMapping,
)

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


def create_yaml_from_xlsx(source, target, sheet_name, col, attrs=[]):
    """Parses an xlsx file with a codelist and writes a yaml file

    Parameters
    ----------
    source : str, path, file-like object
        Path to Excel file with definitions (codelists).
    target : str, path, file-like object
        Path to save the parsed definitions as yaml file.
    sheet_name : str
        Sheet name of `source`.
    col : str
        Column from `sheet_name` to use as codes.
    attrs : list, optional
        Columns from `sheet_name` to use as attributes.
    """
    CodeList.read_excel(
        name="", source=source, sheet_name=sheet_name, col=col, attrs=attrs
    ).to_yaml(target)
