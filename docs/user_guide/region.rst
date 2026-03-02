.. _region:

The *region* codelist
=====================

Each region **must** be part of a hierarchy, which means that the following nested list
structure is required:

.. code:: yaml

   - Hierarchy 1:
     - Region 1:
         description: Some short explanation
         countries: [Country 1, Country 2, ...]
     - Region 2:
         description: Some short explanation
         iso3_codes: ABC
   - Hierarchy 2:
     - ...

Regions can have attributes, for example a description, a list of countries, or ISO3 codes.
If the attributes `countries` and/or `iso3_codes` are provided, the item(s) are 
validated against a list of valid ISO3 country names/codes taken from the
`pycountry <https://github.com/flyingcircusio/pycountry>`_ package.
More details on the list of countries can be found :ref:`here <countries>`.

Common regions
--------------

In model-comparison projects, it is useful to define *common regions* that can be
computed consistently from original model results. Widely used examples are the
R5, R9 and R10 regions, see here_.

.. _here: https://github.com/IAMconsortium/common-definitions/blob/main/definitions/region/common.yaml

Naming conventions for native model regions
-------------------------------------------

In contrast to common regions used for comparison or scenario analysis across models,
each model has a "native region" resolution.

Models with a coarse spatial resolution should add a model-specific *prefix* to the
native model regions (e.g., `MESSAGEix-GLOBIOM 1.1|North America`) to avoid confusion
when comparing results to other models with similar-but-different regions.

.. code:: yaml

   - Model A v1.0:
     - Model A v1.0|Region 1:
         description: Some short explanation

The renaming from (short) region-names as reported by a modelling framework to such
more verbose region names for use in model-comparison projects can be implemented
by the :ref:`model_mapping`.

If a model has a country-level resolution where disambiguation is not a concern,
we recommend to *not add* a model identifier.

Connections between regions
---------------------------

For reporting of connections (e.g., trade flows), "directional regions" can be
defined using a *>* separator. The region before the separator is the *origin*,
the region after the separator is the *destination*.

.. code:: yaml

   - Trade Connections:
     - China>Europe

Both the *origin* and *destination* regions must be defined in the region codelist.

For model-specific directional connections, the *prefix* must be added as well.

.. code:: yaml

   - Model A v1.0 [Connection]:
     - Model A v1.0|Region 1>Region 2

Both origin and destination `Model A v1.0|Region 1` and `Model A v1.0|Region 2` must be
defined in the region codelist.
