.. _cli:

Command line interface
======================

Nomenclature offers CLI (=command line interface) functionality that validates codelists
and model mappings *themselves* (as opposed to input data). This can be very useful to
ensure that all codelists or model mappings for a project are understood by
nomenclature:

.. code-block:: bash

  nomenclature validate-project /folder/where/definitions/and/mappings/are


.. click:: nomenclature:cli
   :prog: nomenclature
   :nested: full
