import logging
from pyam import IamDataFrame, to_list

# define logger for this script at logging level INFO
logger = logging.getLogger(__name__)


def log_error(name, lst):
    """Compile an error message and write to log"""
    msg = f"The following {name} are not defined in the DataStructureDefinition:"
    logger.error("\n - ".join(map(str, [msg] + lst)))


def is_subset(x, y):
    """Check if x is a subset of y (replacing None by "")"""
    return set(to_list(x)).issubset([u or "" for u in to_list(y)])


def validate(dsd, df):
    """Validation of an IamDataFrame against codelists of a DataStructureDefinition"""

    if not isinstance(df, IamDataFrame):
        df = IamDataFrame(df)

    error = False

    # combined validation of variables and units
    invalid_vars, invalid_units = [], []
    for variable, unit in df.unit_mapping.items():
        if variable not in dsd.variable:
            invalid_vars.append(variable)
        else:
            dsd_unit = dsd.variable[variable]["unit"]
            # fast-pass for unique units in df and the DataStructureDefinition
            if dsd_unit == unit:
                continue
            # full-fledged subset validation
            if is_subset(unit, dsd_unit):
                continue
            invalid_units.append((variable, unit, dsd_unit))

    if invalid_vars:
        log_error("variables", invalid_vars)
        error = True

    if invalid_units:
        lst = [f"{v} - expected: {e}, found: {u}" for v, u, e in invalid_units]
        log_error("units", lst)
        error = True

    # loop over other dimensions for validation
    cols = [
        (df.region, dsd.region, "regions"),
    ]

    for values, codelist, name in cols:
        invalid = [c for c in values if c not in codelist]
        if invalid:
            error = True
            log_error(name, invalid)

    if error:
        raise ValueError("The validation failed. Please check the log for details.")

    return True
