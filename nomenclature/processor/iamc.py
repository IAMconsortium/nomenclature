from pydantic import BaseModel, ConfigDict, field_validator

from pyam import IAMC_IDX

from nomenclature.definition import DataStructureDefinition


class IamcDataFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: list[str] | None = None
    scenario: list[str] | None = None
    region: list[str] | None = None
    variable: list[str] | None = None
    unit: list[str] | None = None
    year: list[int] | None = None

    @field_validator(*IAMC_IDX + ["year"], mode="before")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    @property
    def criteria(self):
        return self.model_dump(exclude_none=True, exclude_unset=True)

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        error_msg = ""

        # check for filter-items that are not defined in the codelists
        for dimension in IAMC_IDX:
            codelist = getattr(dsd, dimension, None)
            # no validation if codelist is not defined or filter-item is None
            if codelist is None or getattr(self, dimension) is None:
                continue
            if invalid := codelist.validate_items(getattr(self, dimension)):
                error_msg += (
                    f"The following {dimension}s are not defined in the "
                    "DataStructureDefinition:\n   " + ", ".join(invalid) + "\n"
                )

        if error_msg:
            raise ValueError(error_msg)
