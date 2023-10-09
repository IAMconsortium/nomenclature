import logging
from importlib.metadata import version
from pathlib import Path

from setuptools_scm import get_version

import pandas as pd

from nomenclature.cli import cli  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.core import process  # noqa
from nomenclature.definition import SPECIAL_CODELIST, DataStructureDefinition  # noqa
from nomenclature.processor import (  # noqa
    RegionAggregationMapping,
    RegionProcessor,
    RequiredDataValidator,
)
from nomenclature.countries import countries  # noqa

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


def parse_model_registration(source, file_name):
    """Parses a model registration file and writes the definitions & mapping yaml files

    Parameters
    ----------
    source : str, path, file-like object
        Path to xlsx model registration file.
    file_name : str
        Model-identifier part of the yaml file names.
    """
    model = pd.read_excel(source, sheet_name="Model", usecols="B", nrows=1).iloc[0, 0]
    regions = pd.read_excel(source, sheet_name="Regions", header=2)

    native = "Native region (as submitted)"
    rename = "Native region (as shown in the Explorer)"
    sep = "\n  - "

    common_region_groups = [r for r in regions.columns if r not in [native, rename]]

    # write region definitions file
    with open(f"definitions/region/model_native_regions/{file_name}.yaml", "w") as file:
        file.write(f"- {model}:{sep}" + sep.join(regions[rename].values))

    # write mappings file
    with open(f"mappings/{file_name}.yaml", "w") as file:
        file.write(f"model:{sep}{model}\n")

        # TODO this implementation assumes that a rename-target exists
        rename_mapping = [
            f"{row[native]}: {row[rename]}" for i, row in regions.iterrows()
        ]
        file.write(f"native_regions:{sep}" + sep.join(rename_mapping) + "\n")

        file.write(f"common_regions:\n")
        for group in common_region_groups:
            file.write(f"# {group}\n")
            for common, _regions in regions[[group, native]].groupby(group):
                file.write(f"  - {common}:\n    - ")
                file.write("\n    - ".join(_regions[native].values) + "\n")
