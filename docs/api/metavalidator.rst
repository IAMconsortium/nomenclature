.. _meta-validation:

.. currentmodule:: nomenclature

**MetaValidator**
=================

**Meta-indicator validation** checks if meta-indicators follow allowed values and ranges.

Consider the example below:

.. code:: yaml

  - name: Sustainability Concern|Exceeding Prudent Limit For Geological Carbon Storage|World
    meta: Emissions Diagnostics|Cumulative CCS [2020-2100, Gt CO2]
    validation:
      - warning_level: high
        upper_bound: 1490
      - warning_level: medium
        upper_bound: 1290
  - meta: Project
    values: [Project Name 1, Project Name 2]


Each criteria item contains the **name of the meta column to be validated** and **validation arguments**.  

The name of the column is specified in ``meta`` (also allowed as ``meta_columns_to_validate``).  
For the first criteria item, validation will check the values of column
*"Emissions Diagnostics|Cumulative CCS [2020-2100, Gt CO2]"*.
For the second criteria item, validation will check column *"Project"*.
If multiple columns are specified, the validation fails if *any* value for a given
row fails (e.g.: if Column A fails validation and Column B doesn't, the row
is flagged as failed).
The ``name`` field specifies the meta-indicator column that will be added post-validation
with the validation results (``ok``, ``low``, ``medium``, ``high``, ``error``).

The ``validation`` arguments follow the same rules as :class:`DataValidator`
(see :ref:`data-validation`), but apply exclusively to meta-indicator columns.
In addition, the ``values`` field supports membership checks. In the example
above, the "Project" meta-indicator will be checked for its values being either
*"Project Name 1"* or *"Project Name 2"*.

Standard usage
--------------

.. code-block:: python

  from nomenclature import MetaValidator

  # ...setting directory/file paths and loading dataset

  MetaValidator.from_file("path/to/file.yaml").apply(df)

.. autoclass:: MetaValidator
   :members: from_file, from_codelist, apply, validate_with_definition
