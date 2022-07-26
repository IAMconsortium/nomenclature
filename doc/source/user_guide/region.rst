.. _region:

The *region* codelist
=====================

Each region **must** be part of a hierarchy, which means that the following nested list
structure is required:

.. code:: yaml

   - Hierarchy 1:
     - region 1:
         some attribute: some value
     - region 2
   - Hierachy 2:
     - ...

Useful examples of region attributes are ISO2/3-codes
(https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes)
or the list of countries included in a macro-region (i.e., a continent).
