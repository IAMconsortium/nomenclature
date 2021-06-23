import re
import yaml


def parse_yaml(path, codes, file=None, ext=".yaml", top_level_attr=None):
    """Parse `file` in `path` (or all files in subfolders if `file=None`)"""
    new_codes, tag_dict = [], {}

    # parse all files in path if file is None
    file = file or "**/*"

    # parse all files
    for f in path.glob(f"{file}{ext}"):
        with open(f, "r", encoding="utf-8") as stream:
            _dct = yaml.safe_load(stream)

            # check if this file contains a dictionary with a single, <tag>-style key
            if len(_dct) == 1 and re.match(re.compile("<.*>$"), list(_dct)[0]):
                if list(_dct)[0] in tag_dict:
                    raise ValueError(f"Duplicate tag: {list(_dct)[0]}")
                tag_dict.update(_dct)
                continue

            # if specified, set top-level key as attribute instead
            if top_level_attr is not None:
                _original_dict, _dct = _dct.copy(), dict()
                for top_key, _codes in _original_dict.items():
                    for code, attributes in _codes.items():
                        attributes = attributes or dict()
                        attributes[top_level_attr] = top_key
                        _dct[code] = attributes

            # add `file` attribute to each element and add to main dictionary
            for key, value in _dct.items():
                value["file"] = str(f)
            new_codes.append(_dct)

    return replace_tags(codes, new_codes, tag_dict)


def replace_tags(codes, new_codes, tag_dict):
    """Replace tags in `new_codes` by `tag_dict` and update `code_dict`"""

    # replace tags in code
    for _dict in new_codes:
        for key, value in _dict.items():
            _replace_tags(codes, key, value, tag_dict, 0)

    # `codes` is updated inplace, no return


def _replace_tags(codes, key, value, tag_dict, i):
    """Utility implementation to replace tags by items and update attributes"""

    # if reaching the end of the tag dictionary
    if i == len(tag_dict):
        codes[key] = value
        return

    # check if the i-th <tag> is used in the key
    tag = list(tag_dict)[i]
    if tag in key:
        for tag_key, tag_attrs in tag_dict[tag].items():
            _key = key.replace(tag, tag_key)
            _value = replace_tag_attributes(value, tag, tag_attrs)
            _replace_tags(codes, _key, _value, tag_dict, i + 1)
    else:
        _replace_tags(codes, key, value, tag_dict, i + 1)


def replace_tag_attributes(code_attrs, tag, tag_attrs):
    """Return a copy of `code_attrs` after overwriting the attributes"""

    new_attrs = code_attrs.copy()
    for key, value in tag_attrs.items():
        if key in new_attrs:
            new_attrs[key] = new_attrs[key].replace(tag, value)

    return new_attrs
