import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import pyam
import pydantic
import yaml
from jsonschema import ValidationError, validate
from pyam import IamDataFrame
from pydantic import BaseModel, root_validator, validate_arguments, validator
from pydantic.types import DirectoryPath, FilePath
from pydantic.error_wrappers import ErrorWrapper

from nomenclature.definition import DataStructureDefinition
from nomenclature.codelist import PYAM_AGG_KWARGS
from nomenclature.error.region import (
    ModelMappingCollisionError,
    RegionNameCollisionError,
    RegionNotDefinedError,
)
from nomenclature.processor.utils import get_relative_path


AGG_KWARGS = PYAM_AGG_KWARGS + ["region-aggregation"]

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


class NativeRegion(BaseModel):
    """Defines a model native region.

    Can optionally have a renaming attribute which is applied in the region processing.

    Attributes
    ----------
    name : str
        Name of the model native region.
    rename: Optional[str]
        Optional second name that the region will be renamed to.
    """

    name: str
    rename: Optional[str]

    @property
    def target_native_region(self) -> str:
        """Returns the resulting name, i.e. either rename or, if not given, name.

        Returns
        -------
        str
            Resulting name.
        """
        return self.rename if self.rename is not None else self.name


class CommonRegion(BaseModel):
    """Common region used for model intercomparison.

    Parameters
    ----------
    name : str
        Name of the common region.
    constituent_regions:
        List of strings which refer to the original (not renamed, see
        :class:`NativeRegion`) names of model native regions.
    """

    name: str
    constituent_regions: List[str]


class RegionAggregationMapping(BaseModel):
    """Holds information for region processing on a per-model basis.

    Region processing is comprised of native region selection and potentially renaming
    as well as aggregation to "common regions" (regions used for reporting and
    comparison by multiple models).

    Attributes
    ----------
    model: str
        Name of the model for which RegionAggregationMapping is defined.
    file: FilePath
        File path of the mapping file. Saved mostly for error reporting purposes.
    native_regions: Optional[List[NativeRegion]]
        Optionally, list of model native regions to select and potentially rename.
    common_regions: Optional[List[CommonRegion]]
        Optionally, list of common regions where aggregation will be performed.
    """

    model: str
    file: FilePath
    native_regions: Optional[List[NativeRegion]]
    common_regions: Optional[List[CommonRegion]]

    @validator("native_regions")
    def validate_native_regions(cls, v, values):
        target_names = [nr.target_native_region for nr in v]
        duplicates = [
            item for item, count in Counter(target_names).items() if count > 1
        ]
        if duplicates:
            # Raise the custom RegionNameCollisionError and give the parameters
            # duplicates and file.
            raise RegionNameCollisionError(
                location="native regions", duplicates=duplicates, file=values["file"]
            )
        return v

    @validator("common_regions")
    def validate_common_regions(cls, v, values):
        names = [cr.name for cr in v]
        duplicates = [item for item, count in Counter(names).items() if count > 1]
        if duplicates:
            raise RegionNameCollisionError(
                location="common regions", duplicates=duplicates, file=values["file"]
            )
        return v

    @root_validator()
    def check_native_or_common_regions(cls, values):
        # Check that we have at least one of the two: native and common regions
        if (
            values.get("native_regions") is None
            and values.get("common_regions") is None
        ):
            raise ValueError(
                "At least one of the two: 'native_regions', 'common_regions' must be"
                f"given in {values['file']}"
            )
        return values

    @root_validator()
    def check_illegal_renaming(cls, values):
        """Check if any renaming overlaps with common regions"""
        # Skip if only either native-regions or common-regions are specified
        if values.get("native_regions") is None or values.get("common_regions") is None:
            return values
        native_region_names = {
            nr.target_native_region for nr in values["native_regions"]
        }
        common_region_names = {cr.name for cr in values["common_regions"]}
        overlap = list(native_region_names & common_region_names)
        if overlap:
            raise RegionNameCollisionError(
                location="native and common regions",
                duplicates=overlap,
                file=values["file"],
            )
        return values

    @classmethod
    def from_file(cls, file: Union[Path, str]):
        """Initialize a RegionAggregationMapping from a file.

        Parameters
        ----------
        file : Union[Path, str]
            Path to a yaml file which contains region aggregation information for one
            model.

        Returns
        -------
        RegionAggregationMapping
            The resulting region aggregation mapping.

        Raises
        ------
        ValidationError
            Raised in case there are any errors in the provided yaml mapping file.

        Notes
        -----

        This function is used to convert a model mapping yaml file into a dictionary
        which is used to initialize a RegionAggregationMapping.
        """
        SCHEMA_FILE = here / "../validation_schemas" / "region_mapping_schema.yaml"
        file = Path(file) if isinstance(file, str) else file
        with open(file, "r") as f:
            mapping_input = yaml.safe_load(f)
        with open(SCHEMA_FILE, "r") as f:
            schema = yaml.safe_load(f)

        # Validate the input data using jsonschema
        try:
            validate(mapping_input, schema)
        except ValidationError as e:
            # Add file information in case of error
            raise ValidationError(f"{e.message} in {get_relative_path(file)}")

        # Add the file name to mapping_input
        mapping_input["file"] = get_relative_path(file)

        # Reformat the "native_regions"
        if "native_regions" in mapping_input:
            native_region_list: List[Dict] = []
            for nr in mapping_input["native_regions"]:
                if isinstance(nr, str):
                    native_region_list.append({"name": nr})
                elif isinstance(nr, dict):
                    native_region_list.append(
                        {"name": list(nr)[0], "rename": list(nr.values())[0]}
                    )
            mapping_input["native_regions"] = native_region_list

        # Reformat the "common_regions"
        if "common_regions" in mapping_input:
            common_region_list: List[Dict[str, List[Dict[str, str]]]] = []
            for cr in mapping_input["common_regions"]:
                cr_name = list(cr)[0]
                common_region_list.append(
                    {
                        "name": cr_name,
                        "constituent_regions": cr[cr_name],
                    }
                )
            mapping_input["common_regions"] = common_region_list
        return cls(**mapping_input)

    @property
    def all_regions(self) -> List[str]:
        # For the native regions we take the **renamed** (if given) names
        nr_list = [x.target_native_region for x in self.native_regions or []]
        cr_list = [x.name for x in self.common_regions or []]
        return nr_list + cr_list

    @property
    def model_native_region_names(self) -> List[str]:
        # List of the **original** model native region names
        return [x.name for x in self.native_regions]

    @property
    def rename_mapping(self) -> Dict[str, str]:
        return {r.name: r.target_native_region for r in self.native_regions or []}

    def validate_regions(self, dsd: DataStructureDefinition) -> None:
        if hasattr(dsd, "region"):
            invalid = [c for c in self.all_regions if c not in dsd.region]
            if invalid:
                raise RegionNotDefinedError(region=invalid, file=self.file)


class RegionProcessor(BaseModel):
    """Region aggregation mappings for scenario processing"""

    mappings: Dict[str, RegionAggregationMapping]

    @classmethod
    @validate_arguments
    def from_directory(cls, path: DirectoryPath):
        """Initialize a RegionProcessor from a directory of model-aggregation mappings.

        Parameters
        ----------
        path : DirectoryPath
            Directory which holds all the mappings.

        Returns
        -------
        RegionProcessor
            The resulting region processor object.

        Raises
        ------
        ModelMappingCollisionError
            Raised in case there are multiple mappings defined for the same model.
        """
        mapping_dict: Dict[str, RegionAggregationMapping] = {}
        for file in path.glob("**/*.yaml"):
            mapping = RegionAggregationMapping.from_file(file)
            if mapping.model not in mapping_dict:
                mapping_dict[mapping.model] = mapping
            else:
                raise ModelMappingCollisionError(
                    model=mapping.model,
                    file1=mapping.file,
                    file2=mapping_dict[mapping.model].file,
                )
        return cls(mappings=mapping_dict)

    def validate_mappings(self, dsd: DataStructureDefinition) -> None:
        """Check if all mappings are valid and collect all errors."""
        errors = []
        for mapping in self.mappings.values():
            try:
                mapping.validate_regions(dsd)
            except RegionNotDefinedError as rnde:
                errors.append(ErrorWrapper(rnde, f"mappings -> {mapping.model}"))
        if errors:
            raise pydantic.ValidationError(errors, model=self.__class__)

    def apply(self, df: IamDataFrame, dsd: DataStructureDefinition) -> IamDataFrame:
        processed_dfs: List[IamDataFrame] = []
        for model in df.model:
            model_df = df.filter(model=model)

            # If no mapping is defined the data frame is returned unchanged
            if model not in self.mappings:
                logging.info(f"No region aggregation mapping found for model {model}")
                processed_dfs.append(model_df)
            # Otherwise we first rename, then aggregate
            else:
                # before aggregating, check that all regions are valid
                self.mappings[model].validate_regions(dsd)
                logging.info(
                    f"Applying region aggregation mapping for model {model} from file "
                    f"{self.mappings[model].file}"
                )
                # Rename
                if self.mappings[model].native_regions is not None:
                    processed_dfs.append(
                        model_df.filter(
                            region=self.mappings[model].model_native_region_names
                        ).rename(region=self.mappings[model].rename_mapping)
                    )

                # Aggregate
                if self.mappings[model].common_regions is not None:
                    vars = self._filter_dict_args(model_df.variable, dsd)
                    vars_default_args = [
                        var for var, kwargs in vars.items() if not kwargs
                    ]
                    vars_kwargs = {
                        var: kwargs
                        for var, kwargs in vars.items()
                        if var not in vars_default_args
                    }
                    for cr in self.mappings[model].common_regions:
                        regions = [cr.name, cr.constituent_regions]
                        # First perform 'simple' aggregation (i.e. no aggregation args)
                        processed_dfs.append(
                            model_df.aggregate_region(vars_default_args, *regions)
                        )
                        # Second, special weighted aggregation
                        for var, kwargs in vars_kwargs.items():
                            if "region-aggregation" not in kwargs:
                                processed_dfs.append(
                                    model_df.aggregate_region(var, *regions, **kwargs)
                                )
                            else:
                                for rename_var in kwargs["region-aggregation"]:
                                    for _rename, _kwargs in rename_var.items():
                                        processed_dfs.append(
                                            model_df.aggregate_region(
                                                var,
                                                *regions,
                                                **_kwargs,
                                            ).rename(variable={var: _rename})
                                        )

        return pyam.concat(processed_dfs)

    def _filter_dict_args(
        self, variables, dsd: DataStructureDefinition, keys: Set[str] = AGG_KWARGS
    ) -> Dict[str, Dict]:
        return {
            var: {key: value for key, value in kwargs.items() if key in keys}
            for var, kwargs in dsd.variable.items()
            if var in variables and not kwargs.get("skip-region-aggregation", False)
        }
