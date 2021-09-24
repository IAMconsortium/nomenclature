from pydantic import BaseModel, ValidationError, validator, root_validator
from typing import Dict, Iterable, Optional, List, Union
from pathlib import Path
import yaml


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
    with open(file, "r") as stream:
        mapping_input = yaml.safe_load(stream)
    # check if we have a key called
    # we need a model name and either native or common regions
    if not "model" and ("native_regions" or "common_regions") in mapping_input.keys():
        raise ValueError(
            "Region mapping needs an attribute 'model' and at "
            "least one of the following: 'native_regions',"
            "'common_regions'"
        )
    if "native_regions" in mapping_input.keys():
        native_region_list: List[Dict] = []
        for nr in mapping_input["native_regions"]:
            if isinstance(nr, str):
                native_region_list.append({"name": nr})
            elif isinstance(nr, dict) and len(nr) == 1:
                native_region_list.append(
                    {"name": list(nr)[0], "rename": list(nr.values())[0]}
                )
            else:
                raise ValueError(
                    f"Encountered error with {nr}, "
                    "native_regions can only contain single "
                    "entries, or single name: rename type mappings."
                )
        mapping_input["native_regions"] = native_region_list
    if "common_regions" in mapping_input.keys():
        common_region_list: List[Dict] = []
        for cr in mapping_input["common_regions"]:
            if not isinstance(cr, dict):
                raise ValueError(
                    "Common regions must be defined in the "
                    "following way: ' - name: \n  - "
                    "constituent_region1 ...'"
                )
            common_region_list.append(
                {
                    "name": list(cr)[0],
                    "constituent_regions": [{"name": x} for x in cr[list(cr)[0]]],
                }
            )
        mapping_input["common_regions"] = common_region_list
    return RegionAggregationMapping(**mapping_input)
