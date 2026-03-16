import logging
from datetime import datetime
from pathlib import Path

import git
import pandas as pd
from pyam import IamDataFrame
from pyam.index import replace_index_labels
from pyam.utils import adjust_log_level, write_sheet

from nomenclature.codelist import (
    CodeList,
    MetaCodeList,
    RegionCodeList,
    ScenarioCodeList,
    VariableCodeList,
)
from nomenclature.config import NomenclatureConfig
from nomenclature.exceptions import (
    NomenclatureValidationError,
    TimeDomainError,
    UnknownCodeError,
    WrongUnitError,
)

logger = logging.getLogger(__name__)
SPECIAL_CODELIST = {
    "variable": VariableCodeList,
    "region": RegionCodeList,
    "scenario": ScenarioCodeList,
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

        self.project_folder = path.parent
        self.project = self.project_folder.name.split("-workflow")[0]

        if (file := self.project_folder / "nomenclature.yaml").exists():
            self.config = NomenclatureConfig.from_file(file=file)
        else:
            self.config = NomenclatureConfig()

        try:
            self.repo = git.Repo(self.project_folder)
        except git.InvalidGitRepositoryError:
            self.repo = None

        if not path.is_dir() and not (
            self.config.repositories
            or self.config.definitions.region.country
            or self.config.definitions.region.nuts
        ):
            raise NotADirectoryError(f"Definitions directory not found: {path}")

        self.dimensions = (
            dimensions
            or self.config.dimensions
            or [x.stem for x in path.iterdir() if x.is_dir()]
        )
        if not self.dimensions:
            raise ValueError("No dimensions specified.")

        for dim in self.dimensions:
            codelist_cls = SPECIAL_CODELIST.get(dim, CodeList)
            self.__setattr__(
                dim, codelist_cls.from_directory(dim, path / dim, self.config)
            )
            getattr(self, dim).check_illegal_characters(self.config)

        if empty := [d for d in self.dimensions if not getattr(self, d)]:
            raise ValueError(f"Empty codelist: {', '.join(empty)}")

    def validate(self, df: IamDataFrame, dimensions: list | None = None) -> None:
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

        exceptions: list[Exception] = []
        for dimension in dimensions or self.dimensions:
            try:
                getattr(self, dimension).validate_df(
                    df,
                    dimension,
                    self.project,
                )
            except (UnknownCodeError, WrongUnitError) as e:
                exceptions.append(e)
        try:
            self.config.time_domain.validate_datetime(df)
        except* TimeDomainError as e:
            exceptions.append(e)
        if exceptions:
            raise NomenclatureValidationError("Validation failed, details:", exceptions)

    def check_aggregate(self, df: IamDataFrame, **kwargs) -> pd.DataFrame:
        """Check for consistency of scenario data along the variable hierarchy

        Parameters
        ----------
        df : :class:`pyam.IamDataFrame`
            Scenario data to be checked for consistency along the variable hierarchy.
        kwargs : Tolerance arguments for comparison of values
            Passed to :any:`numpy.isclose` via :any:`pyam.IamDataFrame.check_aggregate`.

        Returns
        -------
        :class:`pandas.DataFrame`
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
                if code not in self.variable.mapping:
                    continue

                attr = self.variable.mapping[code]
                if attr.check_aggregate:
                    components = attr.components

                    # check if multiple lists of components are given for a code
                    if isinstance(components, dict):
                        for name, _components in components.items():
                            error = df.check_aggregate(code, _components, **kwargs)
                            if error is not None:
                                error = _drop_na_aggregate_errors(
                                    df, error, code, _components
                                )
                                if not error.empty:
                                    # append components-name to variable column
                                    error.index = replace_index_labels(
                                        error.index, "variable", [f"{code} [{name}]"]
                                    )
                                    lst.append(error)

                    # else use components provided as single list or pyam-default (None)
                    else:
                        error = df.check_aggregate(code, components, **kwargs)
                        if error is not None:
                            error = _drop_na_aggregate_errors(
                                df, error, code, components
                            )
                            if not error.empty:
                                lst.append(error)

        if lst:
            return pd.concat(lst)
        return pd.DataFrame()

    def to_excel(self, excel_writer, **kwargs):
        """Write the codelists to an xlsx spreadsheet

        Parameters
        ----------
        excel_writer : str or :class:`pathlib.Path`
            File path as string or :class:`pathlib.Path`.
        **kwargs
            Passed to :class:`pandas.ExcelWriter`
        """
        if "engine" not in kwargs:
            kwargs["engine"] = "xlsxwriter"

        with pd.ExcelWriter(excel_writer, **kwargs) as writer:
            # create dataframe with attributes of the DataStructureDefinition
            project = self.project_folder.absolute().parts[-1]
            arg_dict = {
                "project": project,
                "file_created": time_format(datetime.now()),
                "": "",
            }
            if self.repo is not None:
                arg_dict.update(git_attributes(project, self.repo))

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
                getattr(self, dim).to_excel(writer, dim, sort_by_code=True)


def _drop_na_aggregate_errors(
    df: IamDataFrame,
    error: pd.DataFrame,
    variable: str,
    components: list | None,
) -> pd.DataFrame:
    """Drop rows from aggregate check results where data is missing (NaN).

    In pandas >= 3.0, NaN values in IamDataFrame._data are preserved and
    groupby sum converts them to 0.0, causing false positive aggregate
    failures. This function filters those rows out.

    Parameters
    ----------
    df : IamDataFrame
        The scenario data being checked.
    error : pd.DataFrame
        Result from pyam's check_aggregate (with 'variable' and 'components'
        columns).
    variable : str
        The parent variable being checked.
    components : list or None
        Explicit component variables, or None to use pyam's auto-detection.

    Returns
    -------
    pd.DataFrame
        Filtered error DataFrame with false positives removed.
    """
    # Drop rows with NaN in variable or components columns (pandas 2.x compat)
    error = error.dropna()
    if error.empty:
        return error

    # Filter rows where the original variable value was NaN
    # (pandas 3.x converts NaN to 0.0 in groupby sum, causing false positives)
    var_filter = df._apply_filters(variable=variable)
    var_data = df._data[var_filter]
    nan_var_idx = var_data[var_data.isna()].index
    if not nan_var_idx.empty:
        error = error[~error.index.isin(nan_var_idx)]

    if error.empty:
        return error

    # Filter rows where all component values were NaN
    # (their groupby sum becomes 0.0 in pandas 3.x, causing false positives)
    comp_vars = (
        list(df._variable_components(variable))
        if components is None
        else list(components)
    )
    if comp_vars:
        comp_filter = df._apply_filters(variable=comp_vars)
        comp_data = df._data[comp_filter]
        if not comp_data.empty:
            idx_cols = [
                n for n in comp_data.index.names if n not in ("variable", "unit")
            ]
            # Find groups where all component values are NaN (vectorized)
            has_data = comp_data.notna().groupby(level=idx_cols).any()
            all_nan_idx = has_data[~has_data].index
            if not all_nan_idx.empty:
                error_reduced = error.index.droplevel(["variable", "unit"])
                error = error[~error_reduced.isin(all_nan_idx)]

    return error


def time_format(x):
    return x.strftime("%Y-%m-%d %H:%M:%S")


def git_attributes(name, repo):
    if repo.is_dirty():
        raise ValueError(f"Repository '{name}' is dirty")
    return {
        f"{name}.url": repo.remote().url,
        f"{name}.commit_hash": repo.commit(),
        f"{name}.commit_timestamp": time_format(repo.commit().committed_datetime),
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
