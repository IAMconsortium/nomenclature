from pathlib import Path
import yaml
from typing import Dict, Optional
from pydantic import BaseModel, validator
from jsonschema import validate


here = Path(__file__).parent.absolute()


def read_validation_schema(i):
    with open(here / "validation_schemas" / f"{i}_schema.yaml", "r") as f:
        schema = yaml.safe_load(f)
    return schema


SCHEMA_TYPES = ["variable", "tag", "region"]
SCHEMA_MAPPING = dict([(i, read_validation_schema(i)) for i in SCHEMA_TYPES])


class CodeList(BaseModel):
    """A class for nomenclature codelists & attributes"""
    name: str
    mapping: Optional[Dict]

    @validator("mapping")
    def add_mapping(cls, v):
        return v if isinstance(v, dict) else {}

    def __setitem__(self, key, value):
        if key in self.mapping:
            raise ValueError(f"Duplicate {self.name} key: {key}")
        self.mapping[key] = value

    def __getitem__(self, k):
        return self.mapping[k]

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self.mapping)

    def __repr__(self):
        return self.mapping.__repr__()
