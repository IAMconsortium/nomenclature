from nomenclature.processor import Processor
import pyam
from nomenclature.codelist import MetaCodeList
from pathlib import Path


class MetaValidator(Processor):
    def _check_if_values_allowed(
        self, df: pyam.IamDataFrame, meta_indicator, meta_code_list: MetaCodeList
    ) -> pyam.IamDataFrame:
        not_allowed = []
        for value in df.meta[meta_indicator].values:
            if value not in meta_code_list.mapping[meta_indicator].allowed_values:
                not_allowed.append(value)
        if not_allowed:
            raise ValueError(
                f"{not_allowed} meta indicator value(s) in the {meta_indicator} "
                "column are not allowed. Allowed values are "
                f"{meta_code_list.mapping[meta_indicator].allowed_values}"
            )
        return df

    def validate_meta_indicators(
        self, df: pyam.IamDataFrame, path: Path
    ) -> pyam.IamDataFrame:
        meta_code_list = MetaCodeList.from_directory(name="Meta", path=path)
        unrecognized_meta_indicators = []
        for meta_indicator in df.meta.columns:
            if meta_indicator not in meta_code_list.mapping:
                unrecognized_meta_indicators.append(meta_indicator)
            else:
                self._check_if_values_allowed(
                    df=df, meta_indicator=meta_indicator, meta_code_list=meta_code_list
                )
        if unrecognized_meta_indicators:
            raise ValueError(
                f"{unrecognized_meta_indicators} is/are not recognized in the "
                f"meta definitions file at {path}"
            )
        return df

    def apply(self, df: pyam.IamDataFrame) -> pyam.IamDataFrame:
        return df
