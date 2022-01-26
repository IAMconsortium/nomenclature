from pydantic import PydanticValueError


class VariableRenameArgError(PydanticValueError):
    code = "variable_rename_conflict_error"
    msg_template = (
        "Using attribute 'region-aggregation' and arguments '{args}' not supported, "
        "occurred in variable {variable} (file: {file})"
    )


class VariableRenameTargetError(PydanticValueError):
    code = "variable_rename_target_error"
    msg_template = (
        "Rename-target-variable {target} not defined in the DataStructureDefinition, "
        "occurred in attributes of variable '{variable}' (file: {file})"
    )
