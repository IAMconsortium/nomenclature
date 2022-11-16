.. _codelist:

.. currentmodule:: nomenclature

The CodeList class
==================

A :class:`CodeList <nomenclature.codelist.CodeList>` is a list of allowed values
(i.e. codes) and attributes (optional).
In the :class:`nomenclature` package, the codelists are parsed from yaml files.
They contain lists of allowed values for some or all dimensions of the IAMC format
(i.e., model, scenario, region, variable).

The name of a codelist and the scenario data dimension to which it will be applied is
determined by the **name of the folder**. For example, if a codelist is located in a
folder called *variable* it will be used for validation of the "variable" dimension
of a scenario data file.

See the format for a generic codelist below; the dimensions :ref:`variable <variable>`
and :ref:`region <region>` have a special structure and format.

The generic codelist format
---------------------------

In the most simple case, a codelist consists of a list of strings or mappings, e.g.:

.. code:: yaml

  - allowed_value_a
  - allowed_value_b:
      description: A description of allowed_value_b
   - ...

* The yaml file must be formatted as a list (i.e. entries start with a dash '-').
* Entries can either be a string (e.g. 'allowed_value_a') or a nested dictionary
  (see the example of 'allowed_value_b').
* When instantiating a :class:`DataStructureDefinition` with dimensions other than
  'region' and 'variable', a list of *dimensions*  must be provided explicitly.

The "tag" feature
-----------------

To avoid repetition and subsequent errors, any number of yaml files can be used as
“tags” using a list of mappings. There must be only one top-level entry in any yaml file
to be used as tag. The files defining the tags must be named like ``tag_*.yaml``.

.. code:: yaml

   - Tag:
     - Some Key:
         description: a short description of the key

When importing a tagged codelist, any occurrence of ``{Tag}`` in the name of a code will
be replaced by the corresponding element in the Tag dictionary. If the tag does not contain an element with ``{Tag}``, the tag name is used.

As an example, the following variable:

.. code:: yaml

    - Variable|{Tag}:
      description: The description contains {Tag}
      weight: {Tag}


will be translated to:

.. code:: yaml

    - Variable|Some Key:
      description: The description contains a short description of the key
      weight: Some Key

Since the tag contains a *description* attribute is it replaced in the variable. 

Additionally, the variable also contains the attribute *weight* which features
``{Tag}``, which is not in the tag. In this case the tag name *Some Key* is used.
