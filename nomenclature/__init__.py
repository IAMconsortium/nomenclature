import logging
from pathlib import Path
from setuptools_scm import get_version
from importlib.metadata import version

from nomenclature.codes import CodeList  # noqa
from nomenclature.core import DataStructureDefinition, create_yaml_from_xlsx  # noqa
from nomenclature.testing import assert_valid_yaml  # noqa
from nomenclature.region_mapping_models import (  # noqa
    RegionProcessor,
    RegionAggregationMapping,
)

# set up logging
logger = logging.getLogger(__name__)

# get version number either from git (preferred) or metadata
try:
    __version__ = get_version(Path(__file__).parent.parent)
except LookupError:
    __version__ = version("nomenclature")

