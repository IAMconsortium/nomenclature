.. _config:

.. currentmodule:: nomenclature

General project configuration
=============================

The following features can be accessed via a general project configuration file:

* Import codelists and mappings from public GitHub repositories
* Add all countries to the region codelist (details: :ref:`countries`)

Configuration file format
-------------------------

The configuration file **must be** located on the same level as the *mappings* and
*definitions* directories.

The file **must be** in yaml format and named *nomenclature.yaml*.

Importing from an external repository
-------------------------------------

In order to import from an external repository, the configuration file must define the
repository and the repositories key.

The repository has a **name** (in the example below *common-definitions*) and a **url**. Multiple repositories can be used in a single configuration file:

.. code:: yaml

  repositories:
    common-definitions:
      url: https://github.com/IAMconsortium/common-definitions.git/
    legacy-definitions:
      url: https://github.com/IAMconsortium/legacy-definitions.git/

In order for the import to work the url must be given in the above format, i.e. with the
leading *https://* and the trailing *.git/*.

Information from an external repository can either be used for codelists ("definitions")
or model mappings, or both. For each definition dimension, i.e. *region* or *variable*
multiple external repositories can be used as the example below illustrates for
*variable*:

.. code:: yaml

  repositories:
    common-definitions:
      url: https://github.com/IAMconsortium/common-definitions.git/
  definitions:
    region:
      repository: common-definitions
    variable:
      repositories:
        - common-definitions
        - legacy-definitions
  mappings:
    repository: common-definitions

The value in *definitions.region.repository* needs to reference the repository in the
*repositories* section.

For model mappings the process is analogous using *mappings.repository*.


Adding countries to the region codelist
---------------------------------------

By setting *definitions.region.country* as *true* in the configuration file:

.. code:: yaml

  definitions:
    region:
      country: true

the nomenclature package will add all countries to the *region* codelist.

More details on the list of countries can be found here: :ref:`countries`.

Specify dimensions to be read
-----------------------------

The configuration file offers the possibility to set the dimensions which will be read
by *DataStructureDefinition*.

In the below case we specify *region*, *variable* and *scenario* to be read and used for
validation:

.. code:: yaml

  dimensions:
    - region
    - variable
    - scenario
