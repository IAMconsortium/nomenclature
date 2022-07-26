.. _variable:

The *variable* codelist
=======================

An entry in a variable codelist *must be* a mapping (or a :class:`dict` in Python).
It maps the **name** of an allowed variable to, at least, one key-value pair defining
the allowed **unit(s)** for the variable.

This is an example for a valid entry in a variable codelist:

.. code:: yaml

   - Allowed variable name:
       description: A short explanation or definition
       unit: A unit
       <other attribute>: Some text, value, boolean or list (optional)

.. _variable-guidelines:

Variable naming conventions
---------------------------

A variable name should adhere to the following conventions:

*  A *|* (pipe) character indicates levels of hierarchy.
*  Do not use spaces before and after the *|* character, but add a
   space between words (e.g., *Primary Energy|Non-Biomass Renewables*).
*  Do not use abbreviations (e.g, *PHEV*) unless strictly necessary.
*  Do not use abbreviations of statistical operations (*min*, *max*,
   *avg*) but always spell out the word.
*  All words must be capitalised (except for *and*, *w/*, *w/o*, etc.).
*  Add hierarchy levels where it might be useful in the future, e.g.,
   use *Electric Vehicle|Plugin-Hybrid* instead of *Plugin-Hybrid
   Electric Vehicle*.
*  Do not include words like *Level* or *Quantity* in the variable,
   because this should be clear from the context or unit.

Required and recommended attributes
-----------------------------------

The **unit** attribute is **required** and its value should be compatible with the
`iam-units <https://github.com/iamconsortium/units>`_ package.

The unit attribute can be:

* a string -> one allowed unit for the variable
* a list of strings -> a number of allowed units for the variable
* empty -> a *dimensionless* variable

Examples for all three options:

    .. code:: yaml

      - Single unit variable:
          unit: A single unit
      - Multi unit variable:
          unit: [unit 1, unit 2]
      - Dimensionless variable:
          unit:

A **description** attribute with an explanation or definition is recommended.

The yaml format allows *any* number of additional arbitrary named attributes.

.. _region_aggregation_attributes:

Attributes for region aggregation
---------------------------------

There  are several attributes that affect the region-processing by the nomenclature
package. See the section :ref:`model_mapping` for more information.

* By default, all variables are processed using the method
  :meth:`pyam.IamDataFrame.aggregate_region`, which performs a simple summation of all
  subregions.

* Region aggregation for a particular variable can be skipped by using the attribute
  *skip-region-aggregation: true*; see this example:

    .. code:: yaml

       - Some Variable:
           skip-region-aggregation: true

  Setting *skip-region-aggregation: true* only skips the aggregation for the variable
  in question, but it does not remove that variable from the provided scenario data.

* Any attributes which are arguments of
  :meth:`aggregate_region() <pyam.IamDataFrame.aggregate_region>` will
  be passed to that method. Examples include *method* and *weight*.

* The *weight* attribute is optional. If provided, this variable will be used as a weight for
  computing the region.aggregation as a weighted average. The variable given in the *weight*
  attribute **must** be defined in the list of variables.

* It is possible to rename the variable returned by the region processing using
  a *region-aggregation* attribute, which must have a mapping of the target variable to
  arguments of :meth:`aggregate_region() <pyam.IamDataFrame.aggregate_region>`.

  This option can be used to compute several variables as part of the region-processing.
  In the example below, the variable *Price|Carbon* is computed as a weighted average
  using the CO2 emissions as weights, and in addition, the maximum carbon price within
  each aggregate-region is added as a new variable *Price|Carbon (Max)*.

    .. code:: yaml

        - Price|Carbon:
            unit: USD/t CO2
            region-aggregation:
              - Price|Carbon:
                  weight: Emissions|CO2
              - Price|Carbon (Max):
                  method: max

Consistency across the variable hierarchy
-----------------------------------------

The nomenclature package supports the automated validation of data across the
variable hierarchy, i.e., that all sub-categories or components of a variable
sum up to the value of the category. The feature uses the **pyam** method
:meth:`pyam.IamDataFrame.check_aggregate`.

* To activate the aggregation-check, add *check-aggregate: true* as a variable attribute.

* By default, the method uses all sub-categories of the variable name
  i.e., all variables `Final Energy|*` for computing the aggregate of `Final Energy`.

* You can specify the *components* explicitly either as a list of variables
  or as a list of dictionaries to validate along multiple dimensions.

    .. code:: yaml

        - Final Energy:
            definition: Total final energy consumption
            unit: EJ/yr
            check-aggregate: true
            components:
              - By fuel:
                 - Final Energy|Gas
                 - Final Energy|Electricity
                 - ...
              - By sector:
                 - Final Energy|Residential
                 - Final Energy|Industry
                 - ...
        - Final Energy|Industry:
            definition: Final consumption of the industrial sector
            unit: EJ/yr
            check-aggregate: true
            components:
              - Final Energy|Industry|Gas
              - Final Energy|Industry|Electricity

* The method :meth:`DataStructureDefinition.check_aggregate` returns a
  :class:`pandas.DataFrame` with a comparison of the original value and the computed
  aggregate for all variables that fail the validation.
