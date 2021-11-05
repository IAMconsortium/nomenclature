import copy
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

import pydantic
import yaml
from jsonschema import ValidationError, validate
from pydantic import BaseModel, root_validator, validator, validate_arguments
from pydantic.types import FilePath, DirectoryPath

from nomenclature.core import DataStructureDefinition

here = Path(__file__).parent.absolute()

# We take a deep copy of the original __str__ from
# pydantic.error_wrappers.ValidationError. We do this to keep the changes minimally
# invasive and get 'automatic' updates in case of any changes upstream
original__str__ = copy.deepcopy(pydantic.error_wrappers.ValidationError.__str__)

# Define a new __str__ method which adds file information in case it is present.
# Otherwise the original __str__ method is used.


def new__str__(self):
    """Change __str__ from pydantic ValidationError to include the file name if
    present"""
    if "ctx" in self.errors()[0] and "file" in self.errors()[0]["ctx"]:
        return original__str__(self).replace(
            "\n", f" in {self.errors()[0]['ctx']['file']}\n", 1
        )
    return original__str__(self)


# Overwrite the original __str__ with new__str__
pydantic.error_wrappers.ValidationError.__str__ = new__str__

Sequence = Union[List[str], Tuple[str], Set[str]]


class RegionNameCollisionError(ValueError):
    template = "Name collision in {location} for {duplicates}"

    def __init__(self, location: str, duplicates: Sequence, file: Path) -> None:
        self.file = file.relative_to(Path.cwd())
        super().__init__(
            self.template.format(
                location=location,
                duplicates=duplicates,
                rel_file=self.file,
            )
        )


class NativeRegion(BaseModel):
    name: str
    rename: Optional[str]

    @property
    def target_native_region(self):
        return self.rename if self.rename is not None else self.name


class CommonRegion(BaseModel):
    name: str
    constituent_regions: List[NativeRegion]


class RegionAggregationMapping(BaseModel):
    model: str
    file: FilePath
    native_regions: Optional[List[NativeRegion]]
    common_regions: Optional[List[CommonRegion]]

    @validator("native_regions")
    def validate_native_regions(cls, v, values):
        target_names = [nr.target_native_region for nr in v]
        duplicates = [
            item for item, count in Counter(target_names).items() if count > 1
        ]
        if duplicates:
            # Raise the custom RegionNameCollisionError and give the parameters
            # duplicates and file.
            raise RegionNameCollisionError("native regions", duplicates, values["file"])
        return v

    @validator("common_regions")
    def validate_common_regions(cls, v, values):
        names = [cr.name for cr in v]
        duplicates = [item for item, count in Counter(names).items() if count > 1]
        if duplicates:
            raise RegionNameCollisionError("common regions", duplicates, values["file"])
        return v

    @root_validator()
    def check_illegal_renaming(cls, values):
        """Check if any renaming overlaps with common regions"""
        # Skip if only either native-regions or common-regions are specified
        if values.get("native_regions") is None or values.get("common_regions") is None:
            return values
        native_region_names = {
            nr.target_native_region for nr in values["native_regions"]
        }
        common_region_names = {cr.name for cr in values["common_regions"]}
        overlap = list(native_region_names & common_region_names)
        if overlap:
            raise RegionNameCollisionError(
                "native and common regions", overlap, values["file"]
            )
        return values

    @classmethod
    def create_from_region_mapping(cls, file: Union[Path, str]):
        SCHEMA_FILE = here / "validation_schemas" / "region_mapping_schema.yaml"
        with open(file, "r") as f:
            mapping_input = yaml.safe_load(f)
        with open(SCHEMA_FILE, "r") as f:
            schema = yaml.safe_load(f)

        # Validate the input data using jsonschema
        try:
            validate(mapping_input, schema)
        except ValidationError as e:
            # Add file information in case of error
            raise ValidationError(f"{e.message} in {file}")

        # Add the file name to mapping_input
        mapping_input["file"] = file

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

    @property
    def region_names_all(self) -> List[str]:
        nr_list = (
            [x.target_native_region for x in self.native_regions]
            if self.native_regions is not None
            else []
        )
        cr_list = (
            [x.name for x in self.common_regions]
            if self.common_regions is not None
            else []
        )
        return nr_list + cr_list


class ModelMappingCollisionError(ValueError):
    template = "Multiple region aggregation mappings for model {model} in {files}"

    def __init__(
        self, mapping1: RegionAggregationMapping, mapping2: RegionAggregationMapping
    ) -> None:
        files = (
            mapping1.file.relative_to(Path.cwd()),
            mapping2.file.relative_to(Path.cwd()),
        )
        super().__init__(self.template.format(model=mapping1.model, files=files))


class RegionNotDefinedError(ValueError):
    template = "Region(s) {region} in {file} not defined"

    def __init__(self, region, file) -> None:
        self.file = file
        super().__init__(self.template.format(region=region, file=file))


class RegionProcessor(BaseModel):
    """Region aggregation mappings for scenario processing"""

    dsd: DataStructureDefinition
    mappings: Dict[str, RegionAggregationMapping]

    class Config:
        # necessary since DataStructureDefinition is not a pydantic class
        arbitrary_types_allowed = True

    @classmethod
    @validate_arguments(config=dict(arbitrary_types_allowed=True))
    def from_directory(cls, path: DirectoryPath, dsd: DataStructureDefinition):
        mapping_dict: Dict[str, RegionAggregationMapping] = {}
        for file in path.glob("**/*.yaml"):
            mapping = RegionAggregationMapping.create_from_region_mapping(file)
            if mapping.model not in mapping_dict:
                mapping_dict[mapping.model] = mapping
            else:
                raise ModelMappingCollisionError(mapping, mapping_dict[mapping.model])
        return cls(dsd=dsd, mappings=mapping_dict)

    @validator("mappings", each_item=True)
    def validate_mapping(cls, v, values):
        invalid = [c for c in v.region_names_all if c not in values["dsd"].region]
        if invalid:
            raise RegionNotDefinedError(invalid, v.file)
        return v
