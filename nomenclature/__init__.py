import logging
import logging.config
import sys
from importlib.metadata import version
from pathlib import Path

import yaml

import nomenclature.exceptions  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.core import process  # noqa
from nomenclature.countries import countries  # noqa
from nomenclature.definition import DataStructureDefinition  # noqa
from nomenclature.nuts import nuts  # noqa
from nomenclature.processor import (  # noqa
    RegionAggregationMapping,  # noqa
    RegionProcessor,
    RequiredDataValidator,
)

here = Path(__file__).parent

try:
    __IPYTHON__  # type: ignore
    _in_ipython_session = True
except NameError:
    _in_ipython_session = False

_sys_has_ps1 = hasattr(sys, "ps1")


# Logging is only configured by default when used in an interactive environment
# This follows the setup in ixmp4 and pyam
if _in_ipython_session or _sys_has_ps1:
    with open(here / "logging.yaml") as file:
        logging.config.dictConfig(yaml.safe_load(file))

__version__ = version("nomenclature-iamc")
