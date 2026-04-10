from pydantic import ValidationError
import pytest
from pyam import IamDataFrame

from nomenclature.processor import Processor


def test_processor_subclass():
    class ProcessorSubclass(Processor):
        def apply(self, df: IamDataFrame) -> IamDataFrame:
            return df

    input_data = {"variable": ["Emissions|CO2"], "region": ["World"]}
    output_meta = ["Emissions Diagnostics|Year of Net Zero|CO2"]
    processor = ProcessorSubclass(
        input_data=input_data,
        output_meta=output_meta,
    )

    assert processor.input_data == input_data
    assert processor.input_meta is None
    assert processor.output_data is None
    assert processor.output_meta == output_meta

    # check that frozen fields cannot be modified after instantiation
    with pytest.raises(ValidationError, match="Field is frozen"):
        processor.input_data = {"variable": ["Emissions|Kyoto Gases"]}
    with pytest.raises(ValidationError, match="Field is frozen"):
        processor.input_meta = ["Emissions Diagnostics|Cumulative CO2 [2020-2100"]
