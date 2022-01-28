import pandas as pd
import yaml
import logging
from pathlib import Path

from pyam import IamDataFrame
from pyam.utils import write_sheet

from nomenclature.codelist import CodeList
from nomenclature.error.variable import (
    VariableRenameTargetError,
    VariableRenameArgError,
)
from nomenclature.validation import validate

logger = logging.getLogger(__name__)


# arguments of the method `pyam.IamDa
PYAM_AGG_KWARGS = [
    "components",
    "method",
    "weight",
    "drop_negative_weights",
]


class DataStructureDefinition:
    """Definition of datastructure codelists for dimensions used in the IAMC format"""

    def __init__(self, path, dimensions=["region", "variable"]):
        """

        Parameters
        ----------
        path : str or path-like
            The folder with the project definitions.
        dimensions : list of str, optional
            List of :meth:`CodeList` names. Each CodeList is initialized
            from a sub-folder of `path` of that name.
        """
        if not isinstance(path, Path):
            path = Path(path)

        if not path.is_dir():
            raise NotADirectoryError(f"Definitions directory not found: {path}")

        self.dimensions = dimensions
        for dim in self.dimensions:
            self.__setattr__(dim, CodeList.from_directory(dim, path / dim))

        empty = [d for d in self.dimensions if not self.__getattribute__(d)]
        if empty:
            raise ValueError(f"Empty codelist: {', '.join(empty)}")

        # check that any variable region-processing-rename mappings are valid
        if "variable" in self.dimensions:
            items = [
                (name, attrs)
                for (name, attrs) in self.variable.items()
                if "region-aggregation" in attrs
            ]
            for (name, attrs) in items:
                # ensure that there no pyam-aggregation-kwargs and
                conflict_args = [i for i in attrs if i in PYAM_AGG_KWARGS]
                if conflict_args:
                    raise VariableRenameArgError(
                        variable=name,
                        file=attrs["file"],
                        args=conflict_args,
                    )

                # ensure that mapped variables are defined in the nomenclature
                rename_attrs = CodeList(
                    name="region-aggregation", mapping=attrs["region-aggregation"]
                )
                invalid = [v for v in rename_attrs.keys() if v not in self.variable]
                if invalid:
                    raise VariableRenameTargetError(
                        variable=name, file=attrs["file"], target=invalid
                    )

    def validate(self, df: IamDataFrame, dimensions: list = None) -> None:
        """Validate that the coordinates of `df` are defined in the codelists

        Parameters
        ----------
        df : :class:`pyam.IamDataFrame`
            Scenario data to be validated against the codelists of this instance.
        dimensions : list of str, optional
            Dimensions to perform validation (defaults to all dimensions of self)

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If `df` fails validation against any codelist.
        """
        validate(self, df, dimensions=dimensions or self.dimensions)

    def to_excel(self, excel_writer, sheet_name="variable_definitions"):
        """Write the variable codelist to an Excel sheet

        Parameters
        ----------
        excel_writer : path-like, file-like, or :class:`pandas.ExcelWriter` object
            File path or existing ExcelWriter.
        sheet_name : str, optional
            Name of sheet which will contain the CodeList.
        """

        close = False
        if not isinstance(excel_writer, pd.ExcelWriter):
            close = True
            excel_writer = pd.ExcelWriter(excel_writer)

        # write definitions to sheet
        df = (
            pd.DataFrame.from_dict(self.variable, orient="index")
            .reset_index()
            .rename(columns={"index": "variable"})
            .drop(columns="file")
        )
        df.rename(columns={c: str(c).title() for c in df.columns}, inplace=True)

        write_sheet(excel_writer, sheet_name, df)

        # close the file if `excel_writer` arg was a file name
        if close:
            excel_writer.close()


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

    # check for duplicates in the codelist
    duplicate_rows = source[col].duplicated(keep=False).values
    if any(duplicate_rows):
        duplicates = source[duplicate_rows]
        # set index to equal the row numbers to simplify identifying the issue
        duplicates.index = pd.Index([i + 2 for i in duplicates.index])
        msg = f"Duplicate values in the codelist:\n{duplicates.head(20)}"
        raise ValueError(msg + ("\n..." if len(duplicates) > 20 else ""))

    # set `col` as index and cast all attribute-names to lowercase
    variable = source[[col] + attrs].set_index(col)[attrs]
    variable.rename(columns={c: str(c).lower() for c in variable.columns}, inplace=True)

    # translate to list of nested dicts, replace None by empty field, write to yaml file
    stream = yaml.dump(
        [{code: attrs} for code, attrs in variable.to_dict(orient="index").items()]
    )
    with open(target, "w") as file:
        file.write(stream.replace(": .nan\n", ":\n"))
