import logging
from collections import Counter
from pathlib import Path

import yaml
from pyam import IamDataFrame
from pydantic import BaseModel, field_validator, ValidationInfo
from pydantic.types import FilePath
from pydantic_core import PydanticCustomError

from nomenclature.definition import DataStructureDefinition
from nomenclature.error import custom_pydantic_errors
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


class AggregationItem(BaseModel):
    """Item used for aggregation-mapping"""

    name: str
    components: list[str]


class Aggregator(Processor):
    """Aggregation or renaming of an IamDataFrame on a `dimension`"""

    file: FilePath
    dimension: str
    aggregate: list[AggregationItem]

    def apply(self, df: IamDataFrame) -> IamDataFrame:
        """Apply region processing

        Parameters
        ----------
        df : IamDataFrame
            Input data that the region processing is applied to

        Returns
        -------
        IamDataFrame:
            Processed data

        """
        return df.rename(
            mapping={self.dimension: self.rename_mapping},
            check_duplicates=False,
        )

    @property
    def rename_mapping(self):
        rename_dict = {}

        for item in self.aggregate:
            for c in item.components:
                rename_dict[c] = item.name

        return rename_dict

    @field_validator("aggregate")
    def validate_target_names(cls, v, info: ValidationInfo):
        _validate_items([item.name for item in v], info, "Duplicate target")
        return v

    @field_validator("aggregate")
    def validate_components(cls, v, info: ValidationInfo):
        # components have to be unique for creating rename-mapping (component -> target)
        all_components = list()
        for item in v:
            all_components.extend(item.components)
        _validate_items(all_components, info, "Duplicate component")
        return v

    @field_validator("aggregate")
    def validate_target_vs_components(cls, v, info: ValidationInfo):
        # guard against having identical target and component
        _codes = list()
        for item in v:
            _codes.append(item.name)
            _codes.extend(item.components)
        _validate_items(_codes, info, "Non-unique target and component")
        return v

    @property
    def codes(self):
        _codes = list()
        for item in self.aggregate:
            _codes.append(item.name)
            _codes.extend(item.components)
        return _codes

    def validate_with_definition(self, dsd: DataStructureDefinition) -> None:
        error = None
        # check for codes that are not defined in the codelists
        codelist = getattr(dsd, self.dimension, None)
        # no validation if codelist is not defined or filter-item is None
        if codelist is None:
            error = f"Dimension '{self.dimension}' not found in DataStructureDefinition"
        elif invalid := codelist.validate_items(self.codes):
            error = (
                f"The following {self.dimension}s are not defined in the "
                "DataStructureDefinition:\n - " + "\n - ".join(invalid)
            )
        if error:
            raise ValueError(error + "\nin " + str(self.file) + "")

    @classmethod
    def from_file(cls, file: Path | str):
        """Initialize an AggregatorMapping from a file.

        .. code:: yaml

        dimension: <some_dimension>
        aggregate:
          - Target Value:
            - Source Value A
            - Source Value B

        """
        file = Path(file) if isinstance(file, str) else file
        try:
            with open(file, "r", encoding="utf-8") as f:
                mapping_input = yaml.safe_load(f)

            aggregate_list: list[dict[str, list]] = []
            for item in mapping_input["aggregate"]:
                # TODO explicit check that only one key-value pair exists per item
                aggregate_list.append(
                    dict(name=list(item)[0], components=list(item.values())[0])
                )
        except Exception as error:
            raise ValueError(f"{error} in {get_relative_path(file)}") from error
        return cls(
            dimension=mapping_input["dimension"],
            aggregate=aggregate_list,  # type: ignore
            file=get_relative_path(file),
        )


def _validate_items(items, info, _type):
    duplicates = [item for item, count in Counter(items).items() if count > 1]
    if duplicates:
        raise PydanticCustomError(
            *custom_pydantic_errors.AggregationMappingConflict,
            {
                "type": _type,
                "duplicates": duplicates,
                "file": info.data["file"],
            },
        )
