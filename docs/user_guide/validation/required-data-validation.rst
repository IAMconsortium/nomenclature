.. _required-data-validation:

.. currentmodule:: nomenclature

Required data validation
========================

**Required data validation** checks if certain models, variables, regions and/or 
periods of time are covered in the datapoints.

For this, a configuration file specifies the model(s) and dimension(s) expected
in the dataset. These are ``variable``, ``region`` and/or ``year``.
Alternatively, instead of using ``variable``, it is possible to declare measurands,
which jointly specify variables and units.

.. code:: yaml

  description: Required variables for running MAGICC
  model: model_a
  required_data:
    - measurand:
        Emissions|CO2:
          unit: Mt CO2/yr
      region: World
      year: [2020, 2030, 2040, 2050]

In the example above, for *model_a*, the dataset must include datapoints of the
variable *Emissions|CO2* (measured in *Mt CO2/yr*), in the region *World*, for the
years 2020, 2030, 2040 and 2050.

Standard usage
--------------

Run the following in a Python script to check that an IAMC dataset has valid
required data.

.. code-block:: python

  from nomenclature import RequiredDataValidator

  # ...setting directory/file paths and loading dataset

  RequiredDataValidator.from_file(req_data_yaml).apply(df)
