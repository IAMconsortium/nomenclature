from pyam import IAMC_IDX
from pydantic import BaseModel, ConfigDict, field_validator
from toolkit.exceptions import NoTracebackException

from nomenclature.definition import DataStructureDefinition
from nomenclature.exceptions import NoTracebackExceptionGroup


class IamcDataFilter(BaseModel):
    model: list[str] | None = None
    scenario: list[str] | None = None
    region: list[str] | None = None
    variable: list[str] | None = None
    unit: list[str] | None = None
    year: list[int] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator(*IAMC_IDX + ["year"], mode="before")
    @classmethod
    def single_input_to_list(cls, v):
        return v if isinstance(v, list) else [v]

    @property
    def criteria(self):
        return self.model_dump(exclude_none=True, exclude_unset=True)

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        errors = []

        # Check for filter-items that are not defined in the codelists
        for dimension in IAMC_IDX:
            codelist = getattr(dsd, dimension, None)
            # No validation if codelist is not defined or filter-item is None
            if codelist is None or getattr(self, dimension) is None:
                continue
            if invalid := codelist.validate_items(getattr(self, dimension)):
                errors.append(
                    NoTracebackException(
                        f"The following {dimension}s are not defined in the "
                        "DataStructureDefinition:\n   " + ", ".join(invalid)
                    )
                )

        if errors:
            raise NoTracebackExceptionGroup(
                f"Errors in {self.__class__.__name__}", errors
            )
