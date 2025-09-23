import logging
import logging.config
import sys
from importlib.metadata import version
from pathlib import Path

import pandas as pd
import yaml

from nomenclature.cli import cli  # noqa
from nomenclature.codelist import CodeList  # noqa
from nomenclature.core import process  # noqa
from nomenclature.countries import countries  # noqa
from nomenclature.definition import SPECIAL_CODELIST, DataStructureDefinition  # noqa
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


# Logging is only configured by default when used in an interactive environment.
# This follows the setup in ixmp4 and pyam.
if _in_ipython_session or _sys_has_ps1:
    with open(here / "logging.yaml") as file:
        logging.config.dictConfig(yaml.safe_load(file))

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
    # parse Common-Region-Mapping
    region_aggregation_mapping = RegionAggregationMapping.from_file(
        model_registration_file
    )
    file_model_name = "".join(
        x if (x.isalnum() or x in "._- ") else "_"
        for x in region_aggregation_mapping.model[0]
    )
    region_aggregation_mapping.to_yaml(
        output_directory / f"{file_model_name}_mapping.yaml"
    )
    # parse Region-Country-Mapping
    if "Region-Country-Mapping" in pd.ExcelFile(model_registration_file).sheet_names:
        native = "Native region (as reported by the model)"
        constituents = "Country name"
        region_country_mapping = pd.read_excel(
            model_registration_file,
            sheet_name="Region-Country-Mapping",
            header=2,
            usecols=[native, constituents],
        )
        region_country_mapping = (
            region_country_mapping.dropna().groupby(native)[constituents].apply(list)
        )
    else:
        logger.info(
            "No 'Region-Country-Mapping' sheet found in model registration spreadsheet."
        )
        region_country_mapping = pd.DataFrame()
    if native_regions := [
        {
            region_aggregation_mapping.model[
                0
            ]: region_aggregation_mapping.upload_native_regions
        }
    ]:
        if not region_country_mapping.empty:

            def construct_region_mapping(region):
                countries = region_country_mapping.get(region.name, None)
                if countries:
                    return {region.target_native_region: {"countries": countries}}
                return region.target_native_region

            native_regions = [
                construct_region_mapping(region)
                for region in region_aggregation_mapping.native_regions
            ]
            native_regions = [{region_aggregation_mapping.model[0]: native_regions}]
        with open(
            (output_directory / f"{file_model_name}_regions.yaml"),
            "w",
            encoding="utf-8",
        ) as file:
            yaml.dump(native_regions, file)
