import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from jsonschema import validate
from pydantic import BaseModel


class NativeRegion(BaseModel):
    name: str  # name of the region in the incoming data
    rename: Optional[str]  # new name for the scenario explorer
    # this new name can be automatically verfied against
    # the regions defined in definitions/regions/regions.yaml


class CommonRegion(BaseModel):
    name: str  # can also be verfied against the defined regions
    constituent_regions: List[NativeRegion]  # list of native regions


class RegionAggregationMapping(BaseModel):
    model: str  # if we have a list of allowed models we could also verify the model name here
    # we can require that we have to have least either native_regions or
    # aggregation_regions
    native_regions: Optional[List[NativeRegion]]
    common_regions: Optional[List[CommonRegion]]


# should probably be moved inside RegionAggregationMapping as a classmethod
def convert_region_mapping(file: Union[Path, str]) -> RegionAggregationMapping:
    SCHEMA_FILE = Path(__file__).parent.absolute() / "region_mapping_schema.json"
    with open(file, "r") as f:
        mapping_input = yaml.safe_load(f)
    with open(SCHEMA_FILE, "r") as f:
        schema = json.load(f)

    # Validate the input data using a json schema
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
        common_region_list: List[Dict] = []
        if isinstance(mapping_input["common_regions"], list):
            for cr in mapping_input["common_regions"]:
                common_region_list.append(
                    {
                        "name": list(cr)[0],
                        "constituent_regions": [{"name": x} for x in cr[list(cr)[0]]],
                    }
                )
        elif isinstance(mapping_input["common_regions"], dict):
            for name, cr_list in mapping_input["common_regions"].items():
                common_region_list.append(
                    {
                        "name": name,
                        "constituent_regions": [{"name": x} for x in cr_list],
                    }
                )

        mapping_input["common_regions"] = common_region_list
    return RegionAggregationMapping(**mapping_input)
