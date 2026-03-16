.. _nuts:

.. currentmodule:: nomenclature.nuts

NUTS classification
===================

The :class:`nomenclature` package makes use of the :class:`pysquirrel` package
(`link <https://github.com/iiasa/pysquirrel>`_) to provide a utility for region
names based on the `NUTS classification <https://ec.europa.eu/eurostat/web/nuts>`_. 

This feature allows users to define an agreed list of territorial units with 
multiple levels of resolution, adding functionality to facilitate scenario 
analysis and model comparison.

The full list of NUTS regions is accessible via the Eurostat website (`xlsx, 500kB`_).

.. _GitHub: https://github.com/IAMconsortium/nomenclature/blob/main/nomenclature/countries.py

.. _`xlsx, 500kB`: https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx

.. code:: python

  from nomenclature import nuts

  # Access NUTS region information
  nuts.codes       # List of all NUTS codes
  nuts.names       # List of all NUTS region names
  
  # Query specific NUTS levels
  nuts.get(level=3)            # Get all NUTS3 regions
  
  # Query by country
  nuts.get(country_code="AT")  # Get all NUTS regions in Austria

.. currentmodule:: nomenclature.processor.nuts

**NutsProcessor**
=================

The :class:`NutsProcessor` class provides automated aggregation of scenario data
across NUTS regions. It enables automated hierarchical aggregation from NUTS3 to NUTS2, 
NUTS2 to NUTS1, and NUTS1 to country level, using model-specific rules and variable
code lists.

This processor ensures that regional data is consistently aggregated and validated
according to the configured NUTS regions, without the need to manually specify
region aggregation rules.

Consider the example below for configuring a project using NUTS aggregation.
The *nomenclature.yaml* in the project directory is as follows:

.. code:: yaml

  dimensions:
    - region
    - variable
  definitions:
    region:
      nuts:
        nuts-3: [ AT ]
  processors:
    nuts: [ Model A ]

To run aggregation, the following script could be used:

.. code:: python

  import pyam
  from nomenclature import DataStructureDefinition
  from nomenclature.processor import NutsProcessor

  df = pyam.IamDataFrame(data="path/to/file.csv")
  dsd = DataStructureDefinition("definitions")
  processor = NutsProcessor.from_definition(dsd)
  aggregated_data = processor.apply(df)

The data is aggregated for the applicable variables, creating the common region
"Austria" (AT) from its constituent NUTS subregions.
The final countries must be defined in a region definition file or by setting
*definitions.region.country* as *true* in the configuration file
(see :ref:`adding-countries`).        

.. autoclass:: NutsProcessor
   :members: from_definition, apply
