import re
import yaml


def parse_yaml(path, codes, file=None, ext=".yaml"):
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
                    raise ValueError(f"Duplicate tag {list(_dct)[0]}")
                tag_dict.update(_dct)

            # else, add `file` attribute to each element and add to main dictionary
            else:
                for key, value in _dct.items():
                    value["file"] = str(f)
                new_codes.append(_dct)

    return replace_tags(codes, new_codes, tag_dict)


def replace_tags(codes, new_codes, tag_dict):
    """Replace tags in `new_codes` by `tag_dict` and update `code_dict`"""

    # replace tags in code
    for _dict in new_codes:
        for key, value in _dict.items():
            codes[key] = _dict[key]

    # `codes` is updated inplace, no return
