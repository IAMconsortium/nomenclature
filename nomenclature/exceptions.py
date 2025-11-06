import logging
from functools import partial
from typing import Any

from pydantic_core import PydanticCustomError
from toolkit.exceptions import NoTracebackException

logger = logging.getLogger(__name__)


RegionNameCollisionError = partial(
    PydanticCustomError,
    "region_name_collision",
    "Name collision in {location} for {duplicates} in {file}",
)
ExcludeRegionOverlapError = partial(
    PydanticCustomError,
    "exclude_region_overlap",
    (
        "Region(s) {region} can only be present in 'exclude_regions' or "
        "'{region_type}', not both, in {file}."
    ),
)
VariableRenameArgError = partial(
    PydanticCustomError,
    "variable_rename_conflict",
    (
        "Using attribute 'region-aggregation' and arguments {args} not "
        "supported, occurred in variable '{variable}' (file: {file})"
    ),
)
VariableRenameTargetError = partial(
    PydanticCustomError,
    "variable_rename_target",
    (
        "Region-aggregation-target(s) {target} not defined in the "
        "DataStructureDefinition, occurred in variable '{variable}'"
        " (file: {file})"
    ),
)
MissingWeightError = partial(
    PydanticCustomError,
    "missing_weight",
    (
        "The following variables are used as 'weight' for aggregation but "
        "are not defined in the variable codelist:\n{missing_weights}"
    ),
)
RegionNotDefinedError = partial(
    PydanticCustomError,
    "region_not_defined",
    "Region(s)\n{regions}\nin {file}\nnot found in RegionCodeList",
)
ConstituentsNotNativeError = partial(
    PydanticCustomError,
    "constituents_not_native",
    "Constituent region(s)\n{regions}\nin {file} not found in native region(s)",
)
AggregationMappingConflict = partial(
    PydanticCustomError,
    "aggregation_mapping_conflict",
    "{type} {duplicates} in aggregation-mapping in {file}",
)


class NoTracebackExceptionGroup(ExceptionGroup):
    __suppress_traceback__: bool = True


class NomenclatureValidationError(NoTracebackExceptionGroup):
    pass


class UnknownCodeError(NoTracebackException):

    message_template: str = (
        "The following {}(s) are not defined in the {} codelist:\n - {}{}"
    )
    _file_service_address: str = "https://files.ece.iiasa.ac.at"

    def __init__(
        self,
        dimension: str,
        invalid_code_names: list[str],
        project: str | None = None,
    ) -> None:
        complete_message = self.message_template.format(
            dimension,
            dimension,
            "\n - ".join(invalid_code_names),
            (
                f"\n\nPlease refer to {self._file_service_address}/{project}/{project}"
                f"-template.xlsx for the list of allowed {dimension}s."
                if project is not None
                else ""
            ),
        )

        super().__init__(complete_message)


class UnknownRegionError(UnknownCodeError):
    dimension = "region"


class UnknownVariableError(UnknownCodeError):
    dimension = "variable"


class UnknownScenarioError(UnknownCodeError):
    dimension = "scenario"


class WrongUnitError(NoTracebackException):
    message_template: str = (
        "The following variables(s) are reported in the wrong unit:\n - {}{}"
    )
    _file_service_address: str = "https://files.ece.iiasa.ac.at"

    def __init__(
        self,
        invalid_units: list[tuple[Any, Any, Any]],
        project: str | None = None,
    ) -> None:

        formatted_invalid_units = [
            f"'{v}' - expected: {'one of ' if isinstance(e, list) else ''}"
            f"'{e}', found: '{u}'"
            for v, u, e in invalid_units
        ]
        complete_message = self.message_template.format(
            "\n - ".join(formatted_invalid_units),
            (
                f"\n\nPlease refer to {self._file_service_address}/{project}/{project}"
                "-template.xlsx for the list of allowed variable-unit combinations."
                if project is not None
                else ""
            ),
        )

        super().__init__(complete_message)


class TimeDomainError(NoTracebackException):
    pass


class TimeDomainErrorGroup(NoTracebackExceptionGroup):
    pass


class YamlErrorGroup(NoTracebackExceptionGroup):
    pass


class ProcessorErrorGroup(NoTracebackExceptionGroup):
    pass


class CodeListErrorGroup(NoTracebackExceptionGroup):
    pass
