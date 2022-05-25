.. _model_mapping:

Region processing using model mappings
======================================

Model mappings, defined on a per-model basis for region processing serve three different
purposes:

1. Defining a list of model native regions under the key *native_regions* that are to be
   selected (and usually uploaded) from an IAM result. This also serves as an implicit
   exclusion list for model native regions, since only explicitly mentioned regions are
   selected. Any region that not mentioned in *native_regions* will cause an error unless explicitly named in the *exclude_regions* section. This to avoid accidentally forgetting a region.
2. Allowing for renaming of model native regions.
3. Defining how model native regions should be aggregated to common
   regions.


Model mapping format specification
----------------------------------

This example illustrates how such a model mapping looks like:

.. code:: yaml

  model: model_a
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

* The names of the four top level keywords are fixed:

  * *model*
  * *native_regions*
  * *common_regions*
  * *exclude_regions*

* Required properties are:
  
  * *model* and 
  * at least one of *native_regions* and *common_regions*

* Optional properties are:
  * *exclude_regions*

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
   region names. In the above example *region_a* and *region_b* and **not**
   *alternative_name_a*.

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
3. If a variable is is reported for *common_region_1* **as well as** *region_a* and
   *region_b*. The **provided results** take **precedence** over the aggregated ones.
   Additionally, the aggregation is computed and compared to the provided results. If
   there are discrepancies, a warning is written to the logs.
   
   .. note::

      Please note that in case of differences no error is raised. Therefore it is
      necessary to check the logs to find out if there were any differences. This is
      intentional since some differences might be expected.

Using the RegionProcessor class
-------------------------------

Once the appropriate model mappings have been created, using the
:class:`RegionProcessor` class to process IAM result data is straightforward:

.. code:: python

   import pyam
   import nomenclature

   # initialize a RegionProcessor instance from the directory containing model mappings
   rp = RegionProcessor.from_directory("mappings")

   # initialize a DataStructureDefinition
   dsd = DataStructureDefinition("defintions", ["region", "variable"])

   # IAMC formatted input data, to be processed
   data = pyam.IamDataFrame("input_data.xlsx")
   
   # returns the processed data as IamDataFrame
   processed_data = rp.apply(data, dsd)

The DataStructureDefinition instance is required for region processing because it is
used to validate the regions defined in the model mappings and provides information
about variable aggregation (see :ref:`region_aggregation_attributes` for details). The
DataStructureDefinition *must* contain the *region* and *variable* dimensions in order to be used as part of the region processing.

In practice, normally, both region processing *and* validation are desired and so the
use of the :func:`process` function is recommended over calling
``RegionProcessor.apply()`` directly.