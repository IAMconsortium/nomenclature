from pathlib import Path
from pyam import IamDataFrame
from nomenclature.codes import CodeList
from nomenclature.validation import validate


class Nomenclature:
    """A nomenclature with codelists for all dimensions used in the IAMC data format"""

    def __init__(self, path):
        if not isinstance(path, Path):
            path = Path(path)

        if not path.exists():
            raise ValueError(f"Path to definitions does not exist: {path}")

        self.variable = CodeList("variable").parse_files(path / "variables")
        self.region = CodeList("region").parse_files(
            path / "regions", top_level_attr="hierarchy"
        )

    def validate(self, df: IamDataFrame) -> None:
        """Validate that the coordinates of `df` are defined in the codelists

        Parameters
        ----------
        df : IamDataFrame
            An IamDataFrame to be validated against the codelists of this nomenclature.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If `df` fails validation against any codelist.
        """
        validate(self, df)
