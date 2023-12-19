from collections import namedtuple

pydantic_custom_error_config = {
    "RegionNameCollisionError": (
        "region_name_collision",
        "Name collision in {location} for {duplicates} in {file}",
    ),
    "ExcludeRegionOverlapError": (
        "exclude_region_overlap",
        "Region(s) {region} can only be present in 'exclude_regions' or "
        "'{region_type}' in {file}.",
    ),
    "VariableRenameArgError": (
        "variable_rename_conflict_error",
        "Using attribute 'region-aggregation' and arguments {args} not supported, "
        "occurred in variable '{variable}' (file: {file})",
    ),
    "VariableRenameTargetError": (
        "variable_rename_target_error",
        "Region-aggregation-target(s) {target} not defined in the "
        "DataStructureDefinition, occurred in variable '{variable}' (file: {file})",
    ),
    "MissingWeightError": (
        "missing_weight_error",
        "The following variables are used as 'weight' for aggregation but "
        "are not defined in the variable codelist:\n{missing_weights}",
    ),
}

PydanticCustomErrors = namedtuple("PydanticCustomErrors", pydantic_custom_error_config)
pydantic_custom_errors = PydanticCustomErrors(**pydantic_custom_error_config)
