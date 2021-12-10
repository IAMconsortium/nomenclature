import logging
from pathlib import Path
from setuptools_scm import get_version
from importlib.metadata import version

from nomenclature.core import process  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.definition import (  # noqa
    DataStructureDefinition,
    create_yaml_from_xlsx,
)
from nomenclature.cli import cli  # noqa
from nomenclature.processor.region import (  # noqa
    RegionProcessor,
    RegionAggregationMapping,
)


# set up logging
logger = logging.getLogger(__name__)

# get version number either from git (preferred) or metadata
try:
    __version__ = get_version(Path(__file__).parents[1])
except LookupError:
    __version__ = version("nomenclature-iamc")
