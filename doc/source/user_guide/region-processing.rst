.. _region-processing:

Region processing
=================

Partial region aggregation
--------------------------

During the region aggregation process provided and aggregated data are combined in a
process dubbed 'partial region aggregation'.

As an example, consider the following model mapping:

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

The `region-aggregation` attribute (see :ref:`region_aggregation_attributes`) works with
partial region aggregation. If a variable is found in the provided data, it is used over
aggregated results. Any discrepancies between the provided and aggregated data are
written to the log.
