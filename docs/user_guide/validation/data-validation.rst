.. _data-validation:

.. currentmodule:: nomenclature

Data validation
===============

**Data validation** checks if timeseries data values are within specified ranges.

Consider the example below:

.. code:: yaml

  - variable: Primary Energy
    year: 2010
    validation:
      - upper_bound: 5
        lower_bound: 1
      - warning_level: low
        upper_bound: 2.5
        lower_bound: 1
  - variable: Primary Energy|Coal
    year: 2010
    value: 5
    rtol: 2
    atol: 1

Each criteria item contains **data filter arguments** and **validation arguments**.

Data filter arguments include: ``model``, ``scenario``, ``region``, ``variable``,
``unit``, and ``year``.
For the first criteria item, the data is filtered for variable *Primary Energy*
and year 2010.

The ``validation`` arguments include: ``upper_bound``/``lower_bound`` *or*
``value``/``rtol``/``atol`` (relative tolerance, absolute tolerance). Only one
of the two can be set for each ``warning_level``.
The possible levels are: ``error``, ``high``, ``medium``, or ``low``.
For the same data filters, multiple warning levels with different criteria each
can be set. These must be listed in descending order of severity, otherwise a
``ValidationError`` is raised.
In the example, for the first criteria item, the validation arguments are set
for warning level ``error`` (by default, in case of omission) and ``low``,
using bounds.
Flagged datapoints are skipped for lower severity warnings in the same criteria
item (e.g.: if datapoints are flagged for the ``error`` level, they will not be
checked again for ``low``).

The second criteria item (for variable *Primary Energy|Coal*) uses the old notation.
Its use is deprecated for being more verbose (requires each warning level to be
a separate criteria item) and slower to process.

Standard usage
--------------

Run the following in a Python script to check that an IAMC dataset has valid data.

.. code-block:: python

  from nomenclature.processor import DataValidator

  # ...setting directory/file paths and loading dataset

  DataValidator.from_file(data_val_yaml).apply(df)
