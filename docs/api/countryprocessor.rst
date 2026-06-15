.. currentmodule:: nomenclature

**CountryProcessor**
====================

The :class:`CountryProcessor` aggregates country-level data to common regional
definitions in the region codelist.

It is intended for standard regional hierarchies such as ``R5``, ``R9`` and
``R10`` imported from `common-definitions <https://github.com/IAMconsortium/common-definitions>`_.
Unlike the :class:`NutsProcessor`, country aggregation is a single-step
aggregation and does not require a nested hierarchy to be computed level by level.

The processor reads region definitions from the project's region codelist and
looks for entries with hierarchy names containing ``R5``, ``R9`` or ``R10``.
Constituent countries are taken from the ``countries`` or ``iso3_codes``
attributes of those region definitions.

Minimal configuration
---------------------

.. code:: yaml

   repositories:
     common-definitions:
       url: https://github.com/IAMconsortium/common-definitions.git/

   definitions:
     region:
       country: true
       repository:
         name: common-definitions
         include:
           - hierarchy: [R5, R9, R10]

   processors:
     countries-processor: [Model A, Model B]

In this setup, all country codes are added to the region codelist, the R5/R9/R10
region definitions are imported from ``common-definitions``, and the processor is
applied to the listed models.

.. autoclass:: CountryProcessor
   :members: from_definition, regional_aggregates, regional_aggregates_by_level, apply