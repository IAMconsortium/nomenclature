.. _model_mapping:

.. currentmodule:: nomenclature

Region processing using model mappings
======================================

The **nomenclature** package supports automated region aggregation as part of a
scenario processing workflow. The instructions for region aggregation are provided
as a *model mapping*.

Model mapping format specification
----------------------------------

This example illustrates a model mapping:

.. code:: yaml

  model: Model A v1.0
  native_regions:
    - region_a: alternative_name_a
    - region_b
  common_regions:
    - common_region_1:
      - region_a
      - region_b
    - common_region_2:
      - ...
  exclude_regions:
    - region_c
    - ... 

The properties *model* and (at least) one of *native_regions* and *common_regions* are
required in a valid model mapping. See :ref:`region` for more information.

*  *model* (str or list of str): the model name(s) for which the mapping applies.
*  *native_regions* (list): a list of model native regions serves as
   a selection as to which regions to keep.

   *  In the above example *region_a* is to be renamed to
      *alternative_name_a*. This is done by defining a key-value pair
      of *model_native_name: new_name*.
   *  *region_b* is selected but the name is not changed.
   *  Assuming *model_a* also defines a third region *region_c*,
      since it is not mentioned it will be **dropped** from the data.

*  *common_regions* (list): list of common regions which will be computed as aggregates.
   They are defined as list entries which themselves have a list of constituent regions.
   These constituent regions must be model native regions.

   The names of the constituent regions **must** refer to the **original** model native
   region names, i.e., *region_a* and *region_b*, **not** *alternative_name_a*
   in the example shown above.

* *exclude_regions* optional (list of str): If input data for region processing contains
  regions which are not mentioned in *native_regions*, in *common_regions* (as the name
  of a common region or a constituent region) an error will be raised. This is a
  safeguard against silently dropping regions which are not in named in *native_regions*
  or *common_regions*. 
  
  If regions are to be excluded, they can be explicitly named in the *exclude_regions*
  section which causes their presence to no longer raise an error.

Region aggregation
------------------

In order to illustrate how region aggregation is performed, consider the following model
mapping:

.. code:: yaml

   model: model_a  
   common_regions:
     - common_region_1:
       - region_a
       - region_b

If the data provided for region aggregation contains results for *common_region_1* they
are compared and combined according to the following logic:

1. If a variable is **not** reported for *common_region_1*, it is calculated through
   region aggregation of regions *region_a* and *region_b*.
2. If a variable is **only** reported for *common_region_1* level it is used directly.
3. If a variable is reported for *common_region_1* **as well as** *region_a* and
   *region_b*. The **provided results** take **precedence** over the aggregated ones.
   Additionally, the aggregation is computed and compared to the provided results. If
   there are discrepancies, a warning is written to the logs.

   .. note::

      Please note that in case of differences no error is raised. Therefore it is
      necessary to check the logs to find out if there were any differences. This is
      intentional since some differences might be expected.

Computing differences between original and aggregated data
----------------------------------------------------------

In order to get the differences between the original data (e.g., results reported by the model)
and the data aggregated according to the region mapping, perform the following steps:

1. Make sure you have ``pyam-iamc >= 1.7.0`` and ``nomenclature-iamc>=0.10.0`` installed.
2. Clone the workflow directory of your project
3. Navigate to the workflow directory
4. Using a Jupyter notebook or Python script run the following:

.. code:: python

  from pyam import IamDataFrame
  from nomenclature import DataStructureDefinition, RegionProcessor

  data = IamDataFrame("/path/to/your/input/data.xlsx")

  dsd = DataStructureDefinition("definitions")
  processor = RegionProcessor.from_directory("mappings", dsd)

  # get the differences as a pandas dataframe
  # the value for the relative tolerances can be adjusted, defaults to 0.01
  processed_data, differences = processor.check_region_aggregation(data, rtol_difference=0.01)
  # save the result of the region processing
  processed_data.to_excel("results.xlsx")
  # and the differences
  differences.to_excel("differences.xlsx")

Please refer to :py:meth:`RegionProcessor.check_region_aggregation` for details.

Alternatively you can also use the nomenclature cli:

.. code-block:: bash

  $ nomenclature check-region-aggregation /path/to/your/input/data.xlsx
  -w workflow_directory --processed_data results.xlsx --differences differences.xlsx

For cli details please refer to :ref:`cli`.
