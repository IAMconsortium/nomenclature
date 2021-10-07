import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from jsonschema import validate
from pydantic import BaseModel


class NativeRegion(BaseModel):
    name: str
    rename: Optional[str]


class CommonRegion(BaseModel):
    name: str
    constituent_regions: List[NativeRegion]


class RegionAggregationMapping(BaseModel):
    model: str

    native_regions: Optional[List[NativeRegion]]
    common_regions: Optional[List[CommonRegion]]

    @classmethod
    def create_from_region_mapping(cls, file: Union[Path, str]):
        SCHEMA_FILE = Path(__file__).parent.absolute() / "region_mapping_schema.yml"
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
                common_region_list.append(
                    {
                        "name": list(cr)[0],
                        "constituent_regions": [{"name": x} for x in cr[list(cr)[0]]],
                    }
                )
            mapping_input["common_regions"] = common_region_list
        return cls(**mapping_input)
