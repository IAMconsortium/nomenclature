from pathlib import Path


def get_relative_path(path: Path):
    # Get the relative version of `path` relative to `path_relative_to`
    # In case path does not contain `path_relative_to` it is returned unchanged
    return (
        path.relative_to(Path.cwd())
        if path.is_absolute() and Path.cwd() in path.parents
        else path
    )
