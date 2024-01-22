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
        "Region(s) {regions} in {file} not found in RegionCodeList",
    ),
}

PydanticCustomErrors = namedtuple("PydanticCustomErrors", pydantic_custom_error_config)
custom_pydantic_errors = PydanticCustomErrors(**pydantic_custom_error_config)


class ErrorCollector:
    errors: list[Exception]

    def __init__(self) -> None:
        self.errors = []

    def append(self, error: Exception) -> None:
        self.errors.append(error)

    def __repr__(self) -> str:
        error = "error" if len(self.errors) == 1 else "errors"
        error_list_str = "\n".join(
            f"{i+1}. {error}" for i, error in enumerate(self.errors)
        )

        return f"Collected {len(self.errors)} {error}:\n" + textwrap.indent(
            error_list_str, prefix="  "
        )

    def __bool__(self) -> bool:
        return bool(self.errors)
