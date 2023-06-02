.. _region:

The *region* codelist
=====================

Each region **must** be part of a hierarchy, which means that the following nested list
structure is required:

.. code:: yaml

   - Hierarchy 1:
     - region 1:
         description: Some short explanation
         iso3_codes: [ABC, DEF, ...]
     - region 2
         description: Some short explanation
         iso3_codes: GHI
   - Hierachy 2:
     - ...

Regions can have attributes, for example a description or ISO3-codes. If an attribute
`iso3_codes` is provided, the item(s) are validated against a list of valid codes taken
from the `pycountry <https://github.com/flyingcircusio/pycountry>`_ package.

Naming conventions for native model regions
-------------------------------------------

Models with a coarse spatial resolution should add a model-specific identifier to the
native model regions (e.g., `MESSAGEix-GLOBIOM 1.1|North America`) to avoid confusion
when comparing results to other models with similar-but-different regions.

.. code:: yaml

   - Model A:
     - Model A|Region 1:
         description: Some short explanation

The renaming from (short) region-names as reported by a modelling framework to such
more verbose region names for use in model-comparison projects can be implemented
by the :ref:`model_mapping`.

If a model has a country-level resolution where disambiguation is not a concern,
we recommend to *not add* a model identifier.
