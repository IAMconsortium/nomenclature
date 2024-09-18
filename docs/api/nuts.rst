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

The full list of NUTS regions is accessible in Eurostat's `Excel file`_.

.. _GitHub: https://github.com/IAMconsortium/nomenclature/blob/main/nomenclature/countries.py

.. _`Excel template`: https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx

.. code:: python

  from nomenclature import nuts

  # list of NUTS region codes
  nuts.codes
  
  # list of NUTS region names
  nuts.names
