class DuplicateCodeError(ValueError):
    code = "duplicate_code"
    msg_template = "Duplicate item in {name} codelist: {code}"
