.. _codelist:

Codelist
========

A "codelist" (named in reference to code lists in `SDMX <https://sdmx.org/>`_) is a yaml
file that contains a list of allowed values for any **index** dimension of the IAMC
format (model, scenario, region, variable). Which index dimension a code list will
be applied to is determined by the **name of the folder** in which it is located. For
example, if a codelist is located in a folder called ``model/`` it will be applied to
the "model" index dimension. 

A codelist must only contain a single list of allowed values. In the most simple case
the list items are strings, e.g.:

.. code:: yaml

  - allowed_value_a
  - allowed_value_b
  - allowed_value_c
  - ...

In case of the "model" or "scenario" index dimension, such a simple list sufficient.
More details on 

For defining allowed variables and regions, however, the list elements are more complicated, detailed in the following.

.. _variable:

Variable
--------

An entry in a variable code list, **must be** a mapping (translated to python as a
dictionary) maps the **name** of an allowed variable to, at minimum, a key value pair
defining the allowed **unit(s)** for the variable.

This is an example for a valid entry in a variable codelist:

.. code:: yaml

   - Allowed variable name:
     unit: A unit
     description: A short description
     <other attribute>: Some text, value, boolean or list (optional)

The **unit** attribute is **required** and should be compatible with the `iam-units
<https://github.com/iamconsortium/units>`_ package.

The unit attribute can be:
* a string -> one allowed unit for the variable
* a list of strings -> a number of allowed units for the variable 
* empty -> a *dimensionless* variable

examples for all three options:

    .. code:: yaml
      
      - Single unit variable:
        unit: A single unit
      - Multi unit variable:
        unit: [unit 1, unit 2]
      - Dimensionless variable:
        unit:      

While not strictly necessary a *description* attribute with a short description of the
variable is encouraged. 

In principle, *any* number of additional arbitrary named attributes are allowed.
However, with the exception of special region-processing specific attributes (see
:ref:`region_aggregation_attributes`), they will not have any effect on the
functionality of nomenclature.

.. _region_aggregation_attributes:

Optional attributes for region aggregation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* By default, all variables are processed using the method
  :meth:`pyam.IamDataFrame.aggregate_region`, which performs a simple summation of all
  subregions.

* Region aggregation for a particular variable can be skipped by using the attribute
  *skip-region-aggregation* and setting it to ``true``:

    .. code:: yaml

       - Some Variable:
         skip-region-aggregation: true

  Setting *skip-region-aggregation* to ``true`` only skips the variable in question for
  aggregation, if the variable is part of the provided data, it **is** used.

* Any attributes which are arguments of
  :meth:`aggregate_region() <pyam.IamDataFrame.aggregate_region>` will
  be passed to that method. Examples include *method* and *weight*.

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


Guidelines and variable naming conventions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The variable name should adhere to the following conventions:

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

Region
------

As is the case for the "variable" codelist, a region codelist must also follow a
specific structure. 

Each region **must** be part of a hierarchy, which means that the following nested list
structure is required:

.. code:: yaml

   - Hierarchy 1:
     - region 1:
        some attribute: some value
     - region 2
   - Hierachy 2:
     - ...  

Attributes of the **regions**, in the above example *some attribute* of *region 1* are
entirely optional and have no influence on the region-processing.

Nonetheless, they can be very useful, examples are: ISO2/3-codes
(https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes) or the list of countries
included in a macro-region (i.e., a continent or large region).

.. _generic:

Generic
-------

As mentioned in the beginning of this section, for IAMC dimensions other than 'region'
and 'variable' (e.g. 'scenario' or 'model'), the requirements for are more simple: 

.. code:: yaml

   - scenario 1
   - scenario 2:
     description: Something about scenario 1
   - ...



* It must be a list (i.e. entries start with a dash '-') 
* Entries can either be a key value pair (like 'scenario 1') or a simple string (like
  'scenario 2').
* The files belonging to this dimension need to be placed in a folder of the same name 
  as the IAMC dimension to be validated. In our example 'scenario'.
* When instantiating a :class:`DataStructureDefinition` with dimensions other than     
  'region' and 'varaible' a list of **all** dimensions must be provided. If for example, the dimensions *region*, *variable* and *scenario* should be read, the code would look like this:

.. code:: python

   dsd = DataStructureDefinition('definitions', ['region', 'variable', 'scenario'])

  
More details on how to instantiate a DataStructureDefinition can be found in
:ref:`minimum_working_example`.

Tag
---

To avoid repetition (and subsequent errors), any number of yaml files can be used as
“tags” using a list of mappings. There must be only one top-level entry in
any yaml file to be used as tag. The files defining the tags must have a name starting
with ``tag_``.

.. code:: yaml

   - Tag:
     - Some Key:
         description: a short description of the key

When importing a *tag* codelist, any occurrence of ``{Tag}`` in the name of a code will
be replaced by every element in the Tag dictionary. The ``{Tag}`` will also be replaced
in any of the variable attributes.
