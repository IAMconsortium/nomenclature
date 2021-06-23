import logging
from pyam import to_list

# define logger for this script at logging level INFO
logger = logging.getLogger(__name__)


def log_error(name, lst):
    """Compile an error message and write to log"""
    msg = f"The following {name} are not defined in the nomenclature:"
    logger.error("\n - ".join([msg] + lst))


def is_subset(x, y):
    """Check if x is a subset of y"""
    return set(to_list(x)).issubset(to_list(y))


def validate(nc, df):
    """Validation of an IamDataFrame against codelists of a Nomenclature"""

    error = False

    # combined validation of variables and units
    invalid_vars, invalid_units = [], []
    for variable, unit in df.unit_mapping.items():
        if variable not in nc.variable:
            invalid_vars.append(variable)
        else:
            nc_unit = nc.variable[variable]["unit"]
            # fast-pass for unique units in df and the nomenclature
            if nc_unit == unit:
                continue
            # full-fledged subset validation
            if is_subset(unit, nc_unit):
                continue
            invalid_units.append((variable, unit, nc_unit))

    if invalid_vars:
        log_error("variables", invalid_vars)
        error = True

    if invalid_units:
        lst = [f"{v} - expected: {e}, found: {u}" for v, u, e in invalid_units]
        log_error("units", lst)
        error = True

    # loop over other dimenions for validation
    cols = [
        (df.region, nc.region, "regions"),
    ]

    for values, codelist, name in cols:
        invalid = [c for c in values if c not in codelist]
        if invalid:
            error = True
            log_error(name, invalid)

    if error:
        raise ValueError("The validation failed. Please check the log for details.")
