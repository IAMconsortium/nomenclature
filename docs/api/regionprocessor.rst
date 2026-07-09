.. currentmodule:: nomenclature.processor

**RegionProcessor**
===================

.. autoclass:: RegionProcessor
   :members: from_directory, validate_with_definition, apply, check_region_aggregation,
   revert, get_common_region_country_mapping, get_native_region_country_mapping


Country to region processor
---------------------------

The :class:`RegionProcessor` includes a method to aggregate country-level data
to common regional definitions in the region codelist.

One intended use case is standard regional hierarchies such as ``R5``, ``R9`` and
``R10`` imported from `common-definitions <https://github.com/IAMconsortium/common-definitions>`_.
Unlike the :class:`NutsProcessor`, country aggregation is a single-step
aggregation and does not require a nested hierarchy to be computed level by level.

The processor reads region definitions from the project's region codelist and
looks for entries with hierarchy names containing ``R5``, ``R9`` or ``R10``.
Constituent countries are taken from the ``countries`` attributes of those region
definitions.

Minimal configuration
---------------------

.. code:: yaml

   repositories:
     common-definitions:
       url: https://github.com/IAMconsortium/common-definitions.git/

   definitions:
     region:
       repository:
         name: common-definitions
         include:
           - hierarchy: [R5, R9, R10]
       country: true

   processors:
     country: [Model A, Model B]

In this setup, all country names are added to the region codelist, the R5/R9/R10
region definitions are imported from ``common-definitions``, and the country
processor is applied to the listed models.

Creating a country processor
----------------------------

For convenience, the :func:`create_country_processor` function can be used to
create a :class:`RegionProcessor` configured for country-level aggregation.

.. autofunction:: create_country_processor

The :meth:`RegionProcessor.from_country_codelist` method is the core factory
method that generates region aggregation mappings on-the-fly.

.. automethod:: RegionProcessor.from_country_codelist
