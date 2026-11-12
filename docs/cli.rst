.. _cli:

Command line interface
======================

The **nomenclature** package offers a command line interface (CLI) to ensure that
the definitions (i.e., codelists) and model mappings for a project are valid.
This can be useful to ensure that all yaml files can be parsed correctly
and that definitions and mappings are internally consistent.

**Standard usage**

Run the following in a command line to ensure that a project folder is a valid
configuration for the **nomenclature** package.

.. code-block:: bash

  nomenclature validate-project /project/folder/

.. toctree::
   :maxdepth: 1

   cli/validate-yaml
   cli/validate-project
   cli/check-region-aggregation
   cli/export-definitions
   cli/list-missing-variables
   cli/run-workflow
   cli/validate-scenarios
   cli/convert-xlsx-codelist-to-yaml
   cli/parse-model-registration
