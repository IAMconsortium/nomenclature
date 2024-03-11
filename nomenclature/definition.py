import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import git
from pyam import IamDataFrame
from pyam.index import replace_index_labels
from pyam.logging import adjust_log_level
from pyam.utils import write_sheet

from nomenclature.codelist import (
    CodeList,
    RegionCodeList,
    VariableCodeList,
    MetaCodeList,
)
from nomenclature.config import NomenclatureConfig
from nomenclature.validation import validate

logger = logging.getLogger(__name__)
SPECIAL_CODELIST = {
    "variable": VariableCodeList,
    "region": RegionCodeList,
    "meta": MetaCodeList,
}


class DataStructureDefinition:
    """Definition of datastructure codelists for dimensions used in the IAMC format"""

    def __init__(self, path, dimensions=None):
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

        self.working_dir = path.parent

        if (file := self.working_dir / "nomenclature.yaml").exists():
            self.config = NomenclatureConfig.from_file(file=file)
        else:
            self.config = NomenclatureConfig()

        try:
            self.repo = git.Repo(self.working_dir)
        except git.InvalidGitRepositoryError:
            self.repo = None

        if not path.is_dir() and not (
            self.config.repositories or self.config.definitions.region.country
        ):
            raise NotADirectoryError(f"Definitions directory not found: {path}")

        self.dimensions = dimensions or ["region", "variable"]
        for dim in self.dimensions:
            codelist_cls = SPECIAL_CODELIST.get(dim, CodeList)
            self.__setattr__(
                dim, codelist_cls.from_directory(dim, path / dim, self.config)
            )

        if empty := [d for d in self.dimensions if not getattr(self, d)]:
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
                attr = self.variable.mapping[code]
                if attr.check_aggregate:
                    components = attr.components

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

    def to_excel(self, excel_writer, sort_by_code: bool = False, **kwargs):
        """Write the codelists to an xlsx spreadsheet

        Parameters
        ----------
        excel_writer : path-like, file-like, or ExcelWriter object
            File path as string or :class:`pathlib.Path`,
            or existing :class:`pandas.ExcelWriter`.
        sort_by_code : bool, optional
            Sort the codelist before exporting to file.
        **kwargs
            Passed to :class:`pandas.ExcelWriter` (if *excel_writer* is path-like).
        """
        with pd.ExcelWriter(excel_writer, engine="xlsxwriter", **kwargs) as writer:

            # create dataframe with attributes of the DataStructureDefinition
            arg_dict = {
                "project": self.working_dir.absolute().parts[-1],
                "file created": time_format(datetime.now()),
                "": "",
            }
            if self.repo is not None:
                arg_dict.update(git_attributes("", self.repo))

            ret = make_dataframe(arg_dict)

            for key, value in self.config.repositories.items():
                ret = pd.concat(
                    [
                        ret,
                        make_dataframe(git_attributes(key, git.Repo(value.local_path))),
                    ]
                )

            write_sheet(writer, "project", ret)

            # write codelist for each dimensions to own sheet
            for dim in self.dimensions:
                getattr(self, dim).to_excel(writer, dim, sort_by_code)


def time_format(x):
    return x.strftime("%Y-%m-%d %H:%M:%S")


def git_attributes(name, repo):
    return {
        "repository": name,
        "url": repo.remote().url,
        "commit": repo.commit(),
        "timestamp": time_format(repo.commit().committed_datetime),
    }


def make_dataframe(data):
    return (
        pd.DataFrame.from_dict(
            data,
            orient="index",
            columns=["value"],
        )
        .reset_index()
        .rename(columns={"index": "attribute"})
    )
