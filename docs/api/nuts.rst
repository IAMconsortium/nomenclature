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
across NUTS regions. It performs hierarchical aggregation in the following order:

1. NUTS3 → NUTS2
2. NUTS2 → NUTS1
3. NUTS1 → Country
4. Country → European Union (if ≥ 23 of the 27 EU member states are present)
5. Country + UK → European Union and United Kingdom (if the United Kingdom is also present)

The EU-level aggregations (steps 4-5) are only performed if the corresponding
target regions (``European Union`` and ``European Union and United Kingdom``) are
defined in the project's region codelist. If fewer than 23 EU member states are
present in the data, the EU aggregation is skipped silently.

The processor ensures that regional data is consistently aggregated and validated
according to the configured NUTS regions and variable code lists.

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
      country: true
  processors:
    nuts: [ Model A ]

With this configuration, calling :func:`process` will automatically instantiate
and apply the :class:`NutsProcessor`.

.. code:: python

  import pyam
  from nomenclature import DataStructureDefinition, process

  df = pyam.IamDataFrame(data="path/to/file.csv")
  dsd = DataStructureDefinition("definitions")
  aggregated_data = process(df, dsd)

The data is aggregated for the applicable variables, creating the common region
``Austria`` (AT) from its constituent NUTS subregions.
The country-level regions must be defined in a region definition file or by setting
*definitions.region.country* as *true* in the configuration file
(see :ref:`adding-countries`).

.. note::

   Only models listed under ``processors.nuts`` in *nomenclature.yaml* are processed
   by :class:`NutsProcessor`. Data for other models is passed through unchanged.
   If a NUTS region appears in the data for a listed model but the corresponding
   country is missing from ``definitions.region.nuts``, a ``ValueError`` is raised.

.. autoclass:: NutsProcessor
   :members: from_definition, apply
