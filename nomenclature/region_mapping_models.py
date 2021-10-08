from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import Counter

import yaml
from jsonschema import validate
from pydantic import BaseModel, validator, root_validator

here = Path(__file__).parent.absolute()


class NativeRegion(BaseModel):
    name: str
    rename: Optional[str]

    @property
    def upload_name(self):
        return self.rename if self.rename is not None else self.name


class CommonRegion(BaseModel):
    name: str
    constituent_regions: List[NativeRegion]


class RegionAggregationMapping(BaseModel):
    model: str
    native_regions: Optional[List[NativeRegion]]
    common_regions: Optional[List[CommonRegion]]

    @validator("native_regions")
    def validate_native_regions(cls, v):
        upload_names = [nr.upload_name for nr in v]
        doubles = [item for item, count in Counter(upload_names).items() if count > 1]
        if doubles:
            raise ValueError(
                f"Two or more native regions share the same name: {doubles}"
            )
        return v

    @validator("common_regions")
    def validate_common_regions(cls, v):
        names = [cr.name for cr in v]
        doubles = [item for item, count in Counter(names).items() if count > 1]
        if doubles:
            raise ValueError(
                f"Duplicated aggregation mapping to common regions: {doubles}"
            )
        return v

    @root_validator()
    def check_illegal_renaming(cls, values):
        """Check if any renaming overlaps with common regions"""
        if values.get("native_regions") is None or values.get("common_regions") is None:
            return values
        native_region_names = {nr.upload_name for nr in values["native_regions"]}
        common_region_names = {cr.name for cr in values["common_regions"]}
        overlap = list(native_region_names & common_region_names)
        if not overlap:
            return values
        raise ValueError(
            "Conflict between (renamed) native regions and aggregation mapping"
            f" to common regions: {overlap}"
        )

    @classmethod
    def create_from_region_mapping(cls, file: Union[Path, str]):
        SCHEMA_FILE = here / "validation_schemas" / "region_mapping_schema.yaml"
        with open(file, "r") as f:
            mapping_input = yaml.safe_load(f)
        with open(SCHEMA_FILE, "r") as f:
            schema = yaml.safe_load(f)

        # Validate the input data using jsonschema
        validate(mapping_input, schema)

        # Reformat the "native_regions"
        if "native_regions" in mapping_input:
            native_region_list: List[Dict] = []
            for nr in mapping_input["native_regions"]:
                if isinstance(nr, str):
                    native_region_list.append({"name": nr})
                elif isinstance(nr, dict):
                    native_region_list.append(
                        {"name": list(nr)[0], "rename": list(nr.values())[0]}
                    )
            mapping_input["native_regions"] = native_region_list

        # Reformat the "common_regions"
        if "common_regions" in mapping_input:
            common_region_list: List[Dict[str, List[Dict[str, str]]]] = []
            for cr in mapping_input["common_regions"]:
                cr_name = list(cr)[0]
                common_region_list.append(
                    {
                        "name": cr_name,
                        "constituent_regions": [{"name": x} for x in cr[cr_name]],
                    }
                )
            mapping_input["common_regions"] = common_region_list
        return cls(**mapping_input)
