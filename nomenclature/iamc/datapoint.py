from typing import List
from pydantic import BaseModel, field_validator


from nomenclature.definition import DataStructureDefinition

IAMC_DIMENSIONS = ["model", "scenario", "region", "variable", "unit"]


class IamcDataFilter(BaseModel):
    model: List[str] | None = None
    scenario: List[str] | None = None
    region: List[str] | None = None
    variable: List[str] | None = None
    unit: List[str] | None = None
    year: List[int] | None = None

    @field_validator(*IAMC_DIMENSIONS, mode="before")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    def validate(self, dsd: DataStructureDefinition) -> None:
        error_msg = ""

        # check for filter-items that are not defined in the codelists 
        for dimension in IAMC_DIMENSIONS:
            if codelist := getattr(dsd, dimension, None) is None:
                continue
            if invalid := codelist.validate_items(getattr(self, dimension) or []):
                error_msg += (
                    f"The following {dimension}s were not found in the "
                    f"DataStructureDefinition:\n{invalid}\n"
                )

        if error_msg:
            raise ValueError(error_msg)
