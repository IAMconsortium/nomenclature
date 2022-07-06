from pydantic import PydanticValueError


class VariableRenameArgError(PydanticValueError):
    code = "variable_rename_conflict_error"
    msg_template = (
        "Using attribute 'region-aggregation' and arguments {args} not supported, "
        "occurred in variable '{variable}' (file: {file})"
    )


class VariableRenameTargetError(PydanticValueError):
    code = "variable_rename_target_error"
    msg_template = (
        "Region-aggregation-target(s) {target} not defined in the "
        "DataStructureDefinition, occurred in variable '{variable}' (file: {file})"
    )


class MissingWeightError(PydanticValueError):
    code = "missing_weight_error"
    msg_template = (
        "The following variables are used as 'weight' for aggregation but "
        "are not defined in the variable codelist:\n{missing_weights}"
    )
