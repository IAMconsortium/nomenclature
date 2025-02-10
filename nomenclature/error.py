import logging
import textwrap
from collections import namedtuple

pydantic_custom_error_config = {
    "RegionNameCollisionError": (
        "region_name_collision",
        "Name collision in {location} for {duplicates} in {file}",
    ),
    "ExcludeRegionOverlapError": (
        "exclude_region_overlap",
        (
            "Region(s) {region} can only be present in 'exclude_regions' or "
            "'{region_type}' in {file}."
        ),
    ),
    "VariableRenameArgError": (
        "variable_rename_conflict",
        (
            "Using attribute 'region-aggregation' and arguments {args} not "
            "supported, occurred in variable '{variable}' (file: {file})"
        ),
    ),
    "VariableRenameTargetError": (
        "variable_rename_target",
        (
            "Region-aggregation-target(s) {target} not defined in the "
            "DataStructureDefinition, occurred in variable '{variable}'"
            " (file: {file})"
        ),
    ),
    "MissingWeightError": (
        "missing_weight",
        (
            "The following variables are used as 'weight' for aggregation but "
            "are not defined in the variable codelist:\n{missing_weights}"
        ),
    ),
    "RegionNotDefinedError": (
        "region_not_defined",
        "Region(s)\n{regions}\nin {file}\nnot found in RegionCodeList",
    ),
    "ConstituentsNotNativeError": (
        "constituents_not_native",
        "Constituent region(s)\n{regions}\nin {file} not found in native region(s)",
    ),
    "AggregationMappingConflict": (
        "aggregation_mapping_conflict",
        "{type} {duplicates} in aggregation-mapping in {file}",
    ),
}

PydanticCustomErrors = namedtuple("PydanticCustomErrors", pydantic_custom_error_config)
custom_pydantic_errors = PydanticCustomErrors(**pydantic_custom_error_config)


class ErrorCollector:
    errors: list[Exception]
    description: str | None = None

    def __init__(self, description: str = None) -> None:
        self.errors = []
        self.description = description

    def append(self, error: Exception) -> None:
        self.errors.append(error)

    def __repr__(self) -> str:
        error = "error" if len(self.errors) == 1 else "errors"
        error_list_str = "\n".join(
            f"{i + 1}. {error}" for i, error in enumerate(self.errors)
        )

        message = f"Collected {len(self.errors)} {error}"
        if self.description is not None:
            message += f" when checking {self.description}"

        return f"{message}:\n" + textwrap.indent(error_list_str, prefix="  ")

    def __bool__(self) -> bool:
        return bool(self.errors)


def log_error(
    dimension: str,
    error_list,
    project: str | None = None,
) -> None:
    """Compile an error message and write to log"""
    file_service_address = "https://files.ece.iiasa.ac.at"
    msg = f"The following {dimension}(s) are not defined in the {dimension} codelist:"

    logging.error(
        "\n - ".join(map(str, [msg] + error_list))
        + (
            f"\n\nPlease refer to {file_service_address}/{project}/{project}"
            f"-template.xlsx for the list of allowed {dimension}s."
            if project is not None
            else ""
        )
    )
