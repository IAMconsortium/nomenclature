from pathlib import Path


def get_relative_path(path: Path):
    # Get the relative version of `path` relative to `path_relative_to`
    # In case path does not contain `path_relative_to` it is returned unchanged
    if isinstance(path, str):
        return path
    return (
        path.relative_to(Path.cwd())
        if path.is_absolute() and Path.cwd() in path.parents
        else path
    )


# Use rmtree with error handler for Windows readonly files
def handle_remove_readonly(func, path, excinfo):
    import os
    import stat

    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise
