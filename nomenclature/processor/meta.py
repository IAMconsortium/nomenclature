from nomenclature.processor import Processor
import pyam
from nomenclature.codelist import MetaCodeList
from pathlib import Path


class MetaValidator(Processor, Path):
    meta_code_list: MetaCodeList = MetaCodeList.from_directory("meta", Path)

    def apply(df: pyam.IamDataFrame, path: Path) -> pyam.IamDataFrame:
        def _check_if_values_allowed(values, allowed_values) -> pyam.IamDataFrame:
            not_allowed = [value for value in values if value not in allowed_values]
            if not_allowed:
                raise ValueError(
                    f"{not_allowed} meta indicator value(s) in the {meta_indicator} "
                    "column are not allowed. Allowed values are "
                    f"{meta_code_list.mapping[meta_indicator].allowed_values}"
                )
            return df

        meta_code_list = MetaCodeList.from_directory(name="Meta", path=path)
        unrecognized_meta_indicators = []
        for meta_indicator in df.meta.columns:
            if meta_indicator not in meta_code_list.mapping:
                unrecognized_meta_indicators.append(meta_indicator)
            else:
                values = df.meta[meta_indicator].values
                allowed_values = meta_code_list.mapping[meta_indicator].allowed_values
                _check_if_values_allowed(values, allowed_values)
        if unrecognized_meta_indicators:
            raise ValueError(
                f"{unrecognized_meta_indicators} is/are not recognized in the "
                f"meta definitions file at {path}"
            )
        return df
