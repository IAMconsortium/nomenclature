from nomenclature.processor import Processor
import pyam
from nomenclature.codelist import MetaCodeList
from pathlib import Path


class MetaValidator(Processor):
    def __init__(self, name_of_meta_code_list: str, path_to_meta_code_list: Path):
        self.meta_code_list = MetaCodeList.from_directory(
            name_of_meta_code_list, path_to_meta_code_list
        )

    def _check_if_values_allowed(self, values, allowed_values, meta_indicator) -> bool:
        """_summary_

        Args:
            df (pyam.IamDataFrame): _description_
            path (Path): _description_

        Returns:
            pyam.IamDataFrame: _description_

        """
        not_allowed = [value for value in values if value not in allowed_values]
        if not_allowed:
            raise ValueError(
                f"{not_allowed} meta indicator value(s) in the {meta_indicator} "
                "column are not allowed. Allowed values are "
                f"{allowed_values}"
            )
        return True

    def apply(self, df: pyam.IamDataFrame, path: Path) -> pyam.IamDataFrame:
        """_summary_

        Args:
            df (pyam.IamDataFrame): _description_
            path (Path): _description_

        Returns:
            pyam.IamDataFrame: _description_
        """
        unrecognized_meta_indicators = []
        for meta_indicator in df.meta.columns:
            if meta_indicator not in self.meta_code_list.mapping:
                unrecognized_meta_indicators.append(meta_indicator)
            else:
                values = df.meta[meta_indicator].values
                allowed_values = self.meta_code_list.mapping[
                    meta_indicator
                ].allowed_values
                self._check_if_values_allowed(values, allowed_values, meta_indicator)
        if unrecognized_meta_indicators:
            raise ValueError(
                f"{unrecognized_meta_indicators} is/are not recognized in the "
                f"meta definitions file at {path}"
            )
        return df
