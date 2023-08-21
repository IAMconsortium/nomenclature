import logging
from pyam import IamDataFrame
from pyam.utils import to_list

# define logger for this script at logging level INFO
logger = logging.getLogger(__name__)


def log_error(name, lst):
    """Compile an error message and write to log"""
    msg = f"The following items are not defined in the '{name}' codelist:"
    logger.error("\n - ".join(map(str, [msg] + lst)))


def is_subset(x, y):
    """Check if x is a subset of y (replacing None by "")"""
    return set(to_list(x)).issubset([u or "" for u in to_list(y)])


def validate(dsd, df, dimensions):
    """Validation of an IamDataFrame against codelists of a DataStructureDefinition"""

    if not isinstance(df, IamDataFrame):
        df = IamDataFrame(df)

    error = False

    for dim in dimensions:
        if invalid := getattr(dsd, dim).validate_items(getattr(df, dim)):
            log_error(dim, invalid)
            error = True

    if "variable" in dimensions:
        # validation of variable, unit combinations
        invalid_units = []
        for variable, unit in df.unit_mapping.items():
            if variable in dsd.variable:
                dsd_unit = dsd.variable[variable].unit
                # fast-pass for unique units in df and the DataStructureDefinition
                if dsd_unit == unit:
                    continue
                # full-fledged subset validation
                if is_subset(unit, dsd_unit):
                    continue
                invalid_units.append((variable, unit, dsd_unit))

        if invalid_units:
            lst = [
                f"'{v}' - expected: {'one of ' if isinstance(e, list) else ''}"
                f"'{e}', found: '{u}'"
                for v, u, e in invalid_units
            ]
            msg = "The following variable(s) are reported with the wrong unit:"
            logger.error("\n - ".join([msg] + lst))
            error = True

    if error:
        raise ValueError("The validation failed. Please check the log for details.")

    return True
