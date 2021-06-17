from pathlib import Path
from codes import CodeList


class Nomenclature():
    """A nomenclature with codelists for all dimensions used in the IAMC data format"""

    def __init__(self, path):
        if not isinstance(path, Path):
            path = Path(path)

        self.variable = CodeList("variable").parse_path(path / "variable")
