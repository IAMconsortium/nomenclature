import pandas as pd
import logging
from pathlib import Path

from pyam import IamDataFrame
from pyam.index import replace_index_labels
from pyam.logging import adjust_log_level
from pyam.utils import write_sheet

from nomenclature.codelist import CodeList
from nomenclature.validation import validate

logger = logging.getLogger(__name__)


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

    def check_aggregate(self, df: IamDataFrame, **kwargs) -> None:
        """Check for consistency of scenario data along the variable hierarchy

        Parameters
        ----------
        df : :class:`pyam.IamDataFrame`
            Scenario data to be checked for consistency along the variable hierarchy.
        kwargs : Tolerance arguments for comparison of values
            Passed to :any:`numpy.isclose` via :any:`pyam.IamDataFrame.check_aggregate`.

        Returns
        -------
        :class:`pandas.DataFrame` or None
            Data where a variable and its computed aggregate does not match.

        Raises
        ------
        ValueError
            If the :any:`DataStructureDefinition` does not have a *variable* dimension.
        """
        if "variable" not in self.dimensions:
            raise ValueError("Aggregation check requires 'variable' dimension.")

        lst = []

        with adjust_log_level(level="WARNING"):
            for code in df.variable:
                attr = self.variable[code]
                if attr.get("check-aggregate", False):
                    components = attr.get("components", None)

                    # check if multiple lists of components are given for a code
                    if isinstance(components, dict):
                        for name, _components in components.items():
                            error = df.check_aggregate(code, _components, **kwargs)
                            if error is not None:
                                error.dropna(inplace=True)
                                # append components-name to variable column
                                error.index = replace_index_labels(
                                    error.index, "variable", [f"{code} [{name}]"]
                                )
                                lst.append(error)

                    # else use components provided as single list or pyam-default (None)
                    else:
                        error = df.check_aggregate(code, components, **kwargs)
                        if error is not None:
                            lst.append(error.dropna())

        if lst:
            # there may be empty dataframes due to `dropna()` above
            error = pd.concat(lst)
            return error if not error.empty else None

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
