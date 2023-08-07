from pathlib import Path
import pyam
from nomenclature.processor import Processor
from nomenclature.codelist import MetaCodeList


class MetaValidator(Processor):
    """Meta indicator validation and processing class"""

    meta_code_list: MetaCodeList

    def __init__(self, path_to_meta_code_list_files: Path):
        super().__init__(
            meta_code_list=MetaCodeList.from_directory(
                name="meta_code_list", path=path_to_meta_code_list_files
            )
        )

    def _values_allowed(self, values, allowed_values, meta_indicator) -> bool:
        """Checks if the values within a meta indicator column are
        listed in model mapping

        Parameters
        ----------
        values :
            List of values in the meta_indicator column of the df: IamDataFrame.
        allowed_values :
            List of allowed values for the meta_indicator column
        meta_indicator :
            The name of the meta_indicator/column whose values are being checked.

        Returns
        -------
        True : boolean
            If all column elements are listed in model mapping

        Raises
        ------
        ValueError
            *If any of the values in the meta indicator column are not
            listed in model mapping


        """
        not_allowed = [value for value in values if value not in allowed_values]
        if not_allowed:
            raise ValueError(
                f"Invalid value for meta indicator '{meta_indicator}': {repr_list(not_allowed)}\n"
                f"Allowed values: {repr_list(allowed_values)}"
            )
        return True

    def apply(self, df: pyam.IamDataFrame) -> pyam.IamDataFrame:
        """Apply meta indicator validation processing

        Parameters
        ----------
        df (pyam.IamDataFrame)
            Input data whose meta indicators will be validated

        Returns
        -------
        df (pyam.IamDataFrame)
            If all meta indicators and their values are listed in the
            model mapping, the same df is returned.

        Raises
        ------
        ValueError
            *If a meta indicator in the 'df' is not listed in the .yaml
            definition file
        """

        if invalid_meta_indicators := [
            meta_indicator
            for meta_indicator in df.meta.columns
            if meta_indicator not in self.meta_code_list.mapping
        ]:
            raise ValueError(
                f"Invalid meta indicator: {repr_list(invalid_meta_indicators)}\n"
                f"Valid meta indicators: {repr_list(self.meta_code_list.mapping.keys())}"
            )

        for meta_indicator in df.meta.columns:
            self._values_allowed(
                list(set(df.meta[meta_indicator].values)),
                self.meta_code_list.mapping[meta_indicator].allowed_values,
                meta_indicator,
            )
        return df


def repr_list(x):
    return "'" + "', '".join(map(str, x)) + "'"
