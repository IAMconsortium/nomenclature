import logging

from nomenclature.codes import CodeList  # noqa
from nomenclature.core import DataStructureDefinition, create_yaml_from_xlsx  # noqa
from nomenclature.testing import assert_valid_yaml  # noqa
from nomenclature.region_mapping_models import (  # noqa
    RegionProcessor,
    RegionAggregationMapping,
)
from ._version import get_versions


# set up logging
logger = logging.getLogger(__name__)

__version__ = get_versions()["version"]
del get_versions
