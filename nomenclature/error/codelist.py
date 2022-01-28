from pydantic import PydanticValueError


class DuplicateCodeError(PydanticValueError):
    code = "duplicate_code"
    msg_template = "Duplicate item in {name} codelist: {code}"
