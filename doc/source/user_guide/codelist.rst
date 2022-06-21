.. _codelist:

Validation using Codelists
==========================

A codelist is a list of codes (i.e. allowed values). In this package, the codelists are
parsed from yaml files. They contain lists of allowed values for any **index**
dimension of the IAMC format (model, scenario, region, variable). Which index dimension
a codelist will be applied to is determined by the **name of the folder** in which it is
located. For example, if a codelist is located in a folder called ``model/`` it will be
applied to the "model" index dimension. 

Codelist format specification
-----------------------------

In the most simple case, a codelist consists of a list of strings, e.g.:

.. code:: yaml

  - allowed_value_a
  - allowed_value_b
  - allowed_value_c
  - ...


For defining allowed *variables* and *regions*, the list elements are more complicated
than simple strings, detailed in the following.

.. _variable:

Variable
^^^^^^^^

An entry in a variable codelist *must be* a mapping (or a :class:`dict` in Python).
It maps the **name** of an allowed variable to, at least, one key-value pair defining
the allowed **unit(s)** for the variable.

This is an example for a valid entry in a variable codelist:

.. code:: yaml

   - Allowed variable name:
       description: A short explanation or definition
       unit: A unit
       <other attribute>: Some text, value, boolean or list (optional)

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

Please also take a look at the :ref:`variable-guidelines` when proposing new items.

.. _region_aggregation_attributes:

Optional attributes for region aggregation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There  are several attributes that affect the region-processing by the nomenclature
package. See the section :ref:`model_mapping` for more information.

* By default, all variables are processed using the method
  :meth:`pyam.IamDataFrame.aggregate_region`, which performs a simple summation of all
  subregions.

* Region aggregation for a particular variable can be skipped by using the attribute
  *skip-region-aggregation* and setting it to ``true``:

    .. code:: yaml

       - Some Variable:
           skip-region-aggregation: true

  Setting *skip-region-aggregation* to ``true`` only skips the variable in question for
  aggregation. If the variable is part of the provided data, it **is** used.

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

Region
^^^^^^

Each region **must** be part of a hierarchy, which means that the following nested list
structure is required:

.. code:: yaml

   - Hierarchy 1:
     - region 1:
         some attribute: some value
     - region 2
   - Hierachy 2:
     - ...  

Useful examples of region attriutes are: ISO2/3-codes
(https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes)
or the list of countries included in a macro-region (i.e., a continent).

.. _generic:

Generic
^^^^^^^

For IAMC dimensions other than 'region'
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

Tag
^^^

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

Using the DataStructureDefinition class
---------------------------------------

Once the required codelists have been created, validating IAM data against a number of
codelists using the nomenclature package is straightforward:  

.. code:: python

   import pyam
   import nomenclature  
  
   # input path to the folder holing the codelists
   dsd = DataStructureDefinition("definition")
   # data to validate in IAMC format
   data = pyam.IamDataFrame("input_data.xlsx") 
   
   # returns True if the data is valid, raises error otherwise
   dsd.validate(data)

Per default, :class:`DataStructureDefinition` reads in *region* and *variable* codelists
from their respective sub folders inside the ``definition/`` folder. Any different
number of dimensions can be read in by instantiating the ``DataStructureDefinition``
object with an additional list of strings, e.g. ``DataStructureDefinition("definition",
['region', 'variable', 'scenario'])``. This would attempt to read three codelists.

In addition, when running :meth:`DataStructureDefinition.validate`, it can be selected
which dimensions to *validate*. Per default, *all* dimensions which were read at
instantiating are validated, but any subset can be selected by providing a list of
dimensions. In the above example using ``dsd.validate(df, ['scenario'])`` would validate
*only* the *scenario* dimension.

In practice, ``DataStructureDefinition.validate`` is usually not called directly but
rather as part of the :func:`process` function which combines validation and region
processing.
