from pathlib import Path
import pandas as pd
import yaml

from pyam import IamDataFrame
from nomenclature.codes import CodeList
from nomenclature.validation import validate


class Nomenclature:
    """A nomenclature with codelists for all dimensions used in the IAMC data format"""

    def __init__(self, path):
        if not isinstance(path, Path):
            path = Path(path)

        if not path.is_dir():
            raise NotADirectoryError(f"Definitions directory not found: {path}")

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


def create_yaml_from_xlsx(source, target, sheet_name, col, attrs=[]):
    """Parses an xlsx file with a codelist and writes a yaml file

    Parameters
    ----------
    source : str, path, file-like object
        Path to Excel file with definitions (codelists).
    target : str, path, file-like object
        Path to save the parsed definitions as yaml file.
    sheet_name : str
        Sheet name of `source`.
    col : str
        Column from `sheet_name` to use as codes.
    attrs : list, optional
        Columns from `sheet_name` to use as attributes.

    """

    source = pd.read_excel(source, sheet_name=sheet_name)
    variable = source[[col] + attrs].set_index(col)
    variable.rename(columns={c: str(c).lower() for c in variable.columns}, inplace=True)

    with open(target, "w") as file:
        yaml.dump(variable.to_dict(orient="index"), file, default_flow_style=False)
