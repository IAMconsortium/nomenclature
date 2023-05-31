import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple

import numpy as np
import pandas as pd
import pyam
import pydantic
import yaml
from pyam import IamDataFrame
from pyam.logging import adjust_log_level
from pydantic import BaseModel, root_validator, validate_arguments, validator
from pydantic.error_wrappers import ErrorWrapper
from pydantic.types import DirectoryPath, FilePath

from nomenclature.codelist import RegionCodeList, VariableCodeList
from nomenclature.definition import DataStructureDefinition
from nomenclature.error.region import (
    ExcludeRegionOverlapError,
    ModelMappingCollisionError,
    RegionNameCollisionError,
    RegionNotDefinedError,
    RegionAggregationMappingParsingError,
)
from nomenclature.processor import Processor
from nomenclature.processor.utils import get_relative_path

logger = logging.getLogger(__name__)

here = Path(__file__).parent.absolute()


class NativeRegion(BaseModel):
    """Define a model native region.

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
        """Return the resulting name, i.e. either rename or, if not given, name.

        Returns
        -------
        str
            Resulting name.
        """
        return self.rename if self.rename is not None else self.name


class CommonRegion(BaseModel):
    """Common region used for model intercomparison.

    Attributes
    ----------
    name : str
        Name of the common region.
    constituent_regions:
        List of strings which refer to the original (not renamed, see
        :class:`NativeRegion`) names of model native regions.
    """

    name: str
    constituent_regions: List[str]

    @property
    def is_single_constituent_region(self):
        return len(self.constituent_regions) == 1

    @property
    def rename_dict(self):
        if self.is_single_constituent_region:
            return {self.constituent_regions[0]: self.name}
        raise AttributeError(
            "rename_dict is only available for single constituent regions"
        )


class RegionAggregationMapping(BaseModel):
    """Hold information for region processing on a per-model basis.

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

    model: List[str]
    file: FilePath
    native_regions: Optional[List[NativeRegion]]
    common_regions: Optional[List[CommonRegion]]
    exclude_regions: Optional[List[str]]

    @root_validator(pre=True)
    def check_no_additional_attributes(cls, v):
        if illegal_additional_attributes := [
            input_attribute
            for input_attribute in v.keys()
            if input_attribute not in cls.__dict__["__fields__"]
        ]:
            raise ValueError(
                "Illegal attributes in 'RegionAggregationMapping': "
                f"{illegal_additional_attributes} (file {v['file']})"
            )
        return v

    @validator("model", pre=True)
    def convert_to_list(cls, v):
        return pyam.utils.to_list(v)

    @validator("native_regions")
    def validate_native_regions_name(cls, v, values):
        native_names = [nr.name for nr in v]
        duplicates = [
            item for item, count in Counter(native_names).items() if count > 1
        ]
        if duplicates:
            # Raise a RegionNameCollisionError with parameters duplicates and file.
            raise RegionNameCollisionError(
                location="native regions (names)",
                duplicates=duplicates,
                file=values["file"],
            )
        return v

    @validator("native_regions")
    def validate_native_regions_target(cls, v, values):
        target_names = [nr.target_native_region for nr in v]
        duplicates = [
            item for item, count in Counter(target_names).items() if count > 1
        ]
        if duplicates:
            # Raise a RegionNameCollisionError with parameters duplicates and file.
            raise RegionNameCollisionError(
                location="native regions (rename-targets)",
                duplicates=duplicates,
                file=values["file"],
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

    @root_validator(skip_on_failure=True)
    def check_native_or_common_regions(cls, values):
        # Check that we have at least one of the two: native and common regions
        if (
            values.get("native_regions") is None
            and values.get("common_regions") is None
        ):
            raise ValueError(
                "At least one of 'native_regions' and 'common_regions' must be "
                f"provided in {values['file']}"
            )
        return values

    @root_validator(skip_on_failure=True)
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

    @root_validator(skip_on_failure=True)
    def check_exclude_native_region_overlap(cls, values):
        return _check_exclude_region_overlap(values, "native_regions")

    @root_validator(skip_on_failure=True)
    def check_exclude_common_region_overlap(cls, values):
        return _check_exclude_region_overlap(values, "common_regions")

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

        Notes
        -----

        This function is used to convert a model mapping yaml file into a dictionary
        which is used to initialize a RegionAggregationMapping.
        """
        try:
            file = Path(file) if isinstance(file, str) else file
            with open(file, "r") as f:
                mapping_input = yaml.safe_load(f)

            # Add the file name to mapping_input
            mapping_input["file"] = get_relative_path(file)

            # Reformat the "native_regions"
            if "native_regions" in mapping_input:
                native_region_list: List[Dict] = []
                for native_region in mapping_input["native_regions"]:
                    if isinstance(native_region, str):
                        native_region_list.append({"name": native_region})
                    elif isinstance(native_region, dict):
                        native_region_list.append(
                            {
                                "name": list(native_region)[0],
                                "rename": list(native_region.values())[0],
                            }
                        )
                mapping_input["native_regions"] = native_region_list

            # Reformat the "common_regions"
            if "common_regions" in mapping_input:
                common_region_list: List[Dict[str, List[Dict[str, str]]]] = []
                for common_region in mapping_input["common_regions"]:
                    common_region_name = list(common_region)[0]
                    common_region_list.append(
                        {
                            "name": common_region_name,
                            "constituent_regions": common_region[common_region_name],
                        }
                    )
                mapping_input["common_regions"] = common_region_list
        except Exception as error:
            raise RegionAggregationMappingParsingError(
                file=get_relative_path(file), error=str(error)
            ) from error
        return cls(**mapping_input)

    @property
    def all_regions(self) -> List[str]:
        # For the native regions we take the **renamed** (if given) names
        nr_list = [x.target_native_region for x in self.native_regions or []]
        return nr_list + self.common_region_names

    @property
    def model_native_region_names(self) -> List[str]:
        # List of the **original** model native region names
        return [x.name for x in self.native_regions or []]

    @property
    def common_region_names(self) -> List[str]:
        # List of the common region names
        return [x.name for x in self.common_regions or []]

    @property
    def rename_mapping(self) -> Dict[str, str]:
        return {r.name: r.target_native_region for r in self.native_regions or []}

    def validate_regions(self, region_codelist: RegionCodeList) -> None:
        if invalid := region_codelist.validate_items(self.all_regions):
            raise RegionNotDefinedError(region=invalid, file=self.file)

    def check_unexpected_regions(self, df: IamDataFrame) -> None:
        # Raise error if a region in the input data is not used in the model mapping

        if regions_not_found := set(df.region) - set(
            self.model_native_region_names
            + self.common_region_names
            + [
                const_reg
                for comm_reg in self.common_regions or []
                for const_reg in comm_reg.constituent_regions
            ]
            + (self.exclude_regions or [])
        ):
            raise ValueError(
                f"Did not find region(s) {regions_not_found} in 'native_regions', "
                "'common_regions' or 'exclude_regions' in model mapping for "
                f"{self.model} in {self.file}. If they are not meant to be included "
                "in the results add to the 'exclude_regions' section in the model "
                "mapping to silence this error."
            )


class RegionProcessor(Processor):
    """Region aggregation mappings for scenario processing"""

    region_codelist: RegionCodeList
    variable_codelist: VariableCodeList
    mappings: Dict[str, RegionAggregationMapping]

    @classmethod
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def from_directory(cls, path: DirectoryPath, dsd: DataStructureDefinition):
        """Initialize a RegionProcessor from a directory of model-aggregation mappings.

        Parameters
        ----------
        path : DirectoryPath
            Directory which holds all the mappings.
        dsd : DataStructureDefinition
            Instance of DataStructureDefinition used for validation of mappings and
            region aggregation.

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
        errors: List[ErrorWrapper] = []
        for file in (f for f in path.glob("**/*") if f.suffix in {".yaml", ".yml"}):
            try:
                mapping = RegionAggregationMapping.from_file(file)
                for model in mapping.model:
                    if model not in mapping_dict:
                        mapping_dict[model] = mapping
                    else:
                        errors.append(
                            ErrorWrapper(
                                ModelMappingCollisionError(
                                    model=model,
                                    file1=mapping.file,
                                    file2=mapping_dict[model].file,
                                ),
                                "__root__",
                            )
                        )
            except (
                pydantic.ValidationError,
                RegionAggregationMappingParsingError,
            ) as error:
                errors.append(ErrorWrapper(error, "__root__"))

        if errors:
            raise pydantic.ValidationError(errors, model=RegionProcessor)

        if missing_dims := [
            dim for dim in ("region", "variable") if not hasattr(dsd, dim)
        ]:
            raise AttributeError(
                "Provided DataStructureDefinition is missing the following attributes "
                f"{missing_dims}"
            )
        return cls(
            mappings=mapping_dict,
            region_codelist=dsd.region,
            variable_codelist=dsd.variable,
        )

    @validator("mappings", each_item=True)
    def validate_with_definition(cls, v, values):
        """Check if all mappings are valid and collect all errors."""
        v.validate_regions(values["region_codelist"])
        return v

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

        Raises
        ------
        ValueError
            * If *df* contains regions that are not listed in the model mapping, or
            * If the region-processing results in an empty **IamDataFrame**.
        """
        processed_dfs: List[IamDataFrame] = []

        for model in df.model:
            model_df = df.filter(model=model)

            # if no mapping is defined the data frame is returned unchanged
            if model not in self.mappings:
                logger.info(f"No model mapping found for model '{model}'")
                processed_dfs.append(model_df)

            # otherwise we first rename, then aggregate
            else:
                file = self.mappings[model].file
                logger.info(
                    f"Applying region-processing for model '{model}' from '{file}'"
                )
                processed_dfs.append(self._apply_region_processing(model_df)[0])

        res = pyam.concat(processed_dfs)
        self.region_codelist.validate_items(res.region)
        return res

    def check_region_aggregation(
        self, df: IamDataFrame, rtol_difference: float = 0.01
    ) -> Tuple[IamDataFrame, pd.DataFrame]:
        """Return region aggregation results and differences between aggregated and
        model native data

        Parameters
        ----------
        df : IamDataFrame
            Input data
        rtol_difference : float, optional
            limit on the relative tolerance for differences, by default 0.01

        Returns
        -------
        Tuple[IamDataFrame, pd.DataFrame]
            IamDataFrame containing aggregation results and pandas dataframe containing
            the differences
        """
        region_processing_results = [
            self._apply_region_processing(
                df.filter(model=model),
                rtol_difference=rtol_difference,
                return_aggregation_difference=True,
            )
            for model in set(df.model) & set(self.mappings)
        ]
        return pyam.concat(res[0] for res in region_processing_results), pd.concat(
            res[1] for res in region_processing_results
        )

    def _apply_region_processing(
        self,
        model_df: IamDataFrame,
        return_aggregation_difference: bool = False,
        rtol_difference: float = 0.01,
    ) -> Tuple[IamDataFrame, pd.DataFrame]:
        """Apply the region processing for a single model"""
        if len(model_df.model) != 1:
            raise ValueError(
                f"Must be called for a unique model, found: {model_df.model}"
            )
        model = model_df.model[0]

        # before aggregating, check that all regions are valid
        self.mappings[model].validate_regions(self.region_codelist)

        # check for regions not mentioned in the model mapping
        self.mappings[model].check_unexpected_regions(model_df)

        _processed_data: List[pd.Series] = []

        # silence pyam's empty filter warnings
        with adjust_log_level(logger="pyam", level="ERROR"):
            # rename native regions
            if self.mappings[model].native_regions is not None:
                _df = model_df.filter(
                    region=self.mappings[model].model_native_region_names
                )
                if not _df.empty:
                    _processed_data.append(
                        _df.rename(region=self.mappings[model].rename_mapping)._data
                    )

            # aggregate common regions
            if self.mappings[model].common_regions is not None:
                for common_region in self.mappings[model].common_regions:
                    # if a common region is consists of a single native region, rename
                    if common_region.is_single_constituent_region:
                        _df = model_df.filter(
                            region=common_region.constituent_regions[0]
                        ).rename(region=common_region.rename_dict)
                        if not _df.empty:
                            _processed_data.append(_df._data)
                        continue

                    # if there are multiple constituent regions, aggregate
                    regions = [common_region.name, common_region.constituent_regions]

                    # first, perform 'simple' aggregation (no arguments)
                    simple_vars = [
                        var.name
                        for var in self.variable_codelist.vars_default_args(
                            model_df.variable
                        )
                    ]
                    _df = model_df.aggregate_region(
                        simple_vars,
                        *regions,
                    )
                    if _df is not None and not _df.empty:
                        _processed_data.append(_df._data)

                    # second, special weighted aggregation
                    for var in self.variable_codelist.vars_kwargs(model_df.variable):
                        if var.region_aggregation is None:
                            _df = _aggregate_region(
                                model_df,
                                var.name,
                                *regions,
                                **var.pyam_agg_kwargs,
                            )
                            if _df is not None and not _df.empty:
                                _processed_data.append(_df._data)
                        else:
                            for rename_var in var.region_aggregation:
                                for _rename, _kwargs in rename_var.items():
                                    _df = _aggregate_region(
                                        model_df,
                                        var.name,
                                        *regions,
                                        **_kwargs,
                                    )
                                    if _df is not None and not _df.empty:
                                        _processed_data.append(
                                            _df.rename(
                                                variable={var.name: _rename}
                                            )._data
                                        )

            common_region_df = model_df.filter(
                region=self.mappings[model].common_region_names,
                variable=self.variable_codelist,
            )

            # concatenate and merge with data provided at common-region level
            difference = pd.DataFrame()
            if _processed_data:
                _data = pd.concat(_processed_data)
                if not common_region_df.empty:
                    _data, difference = _compare_and_merge(
                        common_region_df._data,
                        _data,
                        rtol_difference,
                        return_aggregation_difference,
                    )

            # if data exists only at the common-region level
            elif not common_region_df.empty:
                _data = common_region_df._data

            # raise an error if region-processing yields an empty result
            else:
                raise ValueError(
                    f"Region-processing for model '{model}' returned an empty dataset"
                )

        # cast processed timeseries data and meta indicators to IamDataFrame
        return IamDataFrame(_data, meta=model_df.meta), difference


def _aggregate_region(df, var, *regions, **kwargs):
    """Perform region aggregation with kwargs catching inconsistent-index errors"""
    try:
        return df.aggregate_region(var, *regions, **kwargs)
    except ValueError as error:
        if str(error) == "Inconsistent index between variable and weight!":
            logger.info(
                f"Could not aggregate '{var}' for region '{regions[0]}' ({kwargs})"
            )
        else:
            raise error


def _compare_and_merge(
    original: pd.Series,
    aggregated: pd.Series,
    rtol: float = 0.01,
    return_aggregation_difference: bool = False,
) -> Tuple[IamDataFrame, pd.DataFrame]:
    """Compare and merge original and aggregated results"""

    # compare processed (aggregated) data and data provided at the common-region level
    compare = pd.merge(
        left=original.rename(index="original"),
        right=aggregated.rename(index="aggregated"),
        how="outer",
        left_index=True,
        right_index=True,
    )

    # drop rows that are not in conflict
    compare = compare.dropna()
    difference = compare[
        ~np.isclose(compare["original"], compare["aggregated"], rtol=rtol)
    ]
    difference["difference (%)"] = 100 * np.abs(
        (difference["original"] - difference["aggregated"]) / difference["original"]
    )
    difference = difference.sort_values("difference (%)", ascending=False)
    if difference is not None and len(difference):
        with pd.option_context("display.max_columns", None):
            logger.warning(
                f"Difference between original and aggregated data:\n{difference}"
            )
    if not return_aggregation_difference:
        logger.info(
            "Please refer to the user guide of the nomenclature package "
            "(file:///home/hackstock/Documents/code/nomenclature/doc/build/html/"
            "user_guide/model-mapping.html#computing-differences-between"
            "-original-and-aggregated-data) for obtaining the differences as "
            "dataframe or file."
        )
    # merge aggregated data onto original common-region data
    index = aggregated.index.difference(original.index)
    return pd.concat([original, aggregated[index]]), difference


def _check_exclude_region_overlap(values: Dict, region_type: str) -> Dict:
    if values.get("exclude_regions") is None or values.get(region_type) is None:
        return values
    if overlap := set(values["exclude_regions"]) & {
        r.name for r in values[region_type]
    }:
        raise ExcludeRegionOverlapError(
            region=overlap, region_type=region_type, file=values["file"]
        )
    return values
