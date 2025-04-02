import re
from pyam.str import escape_regexp


def filter_codes(codes, include=None, exclude=None):
    """
    Filter a list of codes based on include and exclude filters.

    Parameters
    ----------
    codes : list[Code]
        List of Code objects to filter.
    include : list[dict[str, Any]], optional
        List of attribute-value mappings to include.
    exclude : list[dict[str, Any]], optional
        List of attribute-value mappings to exclude.

    Returns
    -------
    list[Code]
        Filtered list of Code objects.
    """

    def matches_filter(code, filters, keep):
        def check_attribute_match(code_value, filter_value):
            # if is list -> recursive
            # if is str -> escape all special characters except "*" and use a regex
            # if is int -> match exactly
            # if is None -> Attribute does not exist therefore does not match
            if isinstance(filter_value, int):
                return code_value == filter_value
            if isinstance(filter_value, str):
                pattern = re.compile(escape_regexp(filter_value) + "$")
                return re.match(pattern, code_value) is not None
            if isinstance(filter_value, list):
                return any(
                    check_attribute_match(code_value, value) for value in filter_value
                )
            if filter_value is None:
                return False
            raise ValueError("Invalid filter value type")

        return (
            any(
                all(
                    check_attribute_match(getattr(code, attr, None), value)
                    for attr, value in filter.items()
                )
                for filter in filters
            )
            if filters
            else keep
        )

    filtered_codes = [
        code
        for code in codes
        if matches_filter(code, include, True)
        and not matches_filter(code, exclude, False)
    ]
    return filtered_codes
