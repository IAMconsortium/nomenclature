from pydantic import PydanticValueError


class RegionNameCollisionError(PydanticValueError):
    code = "region_name_collision"
    msg_template = "Name collision in {location} for {duplicates} in {file}"


class ModelMappingCollisionError(PydanticValueError):
    code = "model_mapping_collision"
    msg_template = (
        "Multiple region aggregation mappings for model {model} in [{file1}, {file2}]"
    )


class RegionNotDefinedError(PydanticValueError):
    code = "region_not_defined"
    msg_template = (
        "Region(s) {region} in {file} not defined in the DataStructureDefinition"
    )


class ExcludeRegionOverlapError(PydanticValueError):
    code = "exclude_region_overlap"
    msg_template = (
        "Region(s) {region} can only be present in 'exclude_regions' or "
        "'{region_type}' in {file}."
    )
