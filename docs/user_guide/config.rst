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

The value in *definitions.region.repository* can be a list or a single value.

For model mappings the process is analogous using *mappings.repository*.

Filter code lists imported from external repositories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since importing the entirety of, for example, common-definitions is too much for most
projects, the list can be filtered using ``include`` and ``exclude`` keywords. Under
these keywords, lists of filters can be given that will be applied to the code list from
the given repository.

The filtering can be done by any attribute:

.. code:: yaml

  repositories:
    common-definitions:
      url: https://github.com/IAMconsortium/common-definitions.git/
  definitions:
    variable:
      repository:
        name: common-definitions
        include:
          - name: [Primary Energy*, Final Energy*]
          - name: "Population*"
            tier: 1
        exclude:
          - name: "Final Energy|Industry*"
            depth: 2

If a filter is being used for repositories, the *name* attribute **must be used**
for the repository.

In the example above we are including:
1. All variables starting with *Primary Energy* or *Final Energy*
2. All variables starting with *Population* **and** with the tier attribute equal to 1

From this list we are then **excluding** all variables that match "Final
Energy|Industry\*" and have a depth of 2 (meaning that they contain two pipe "|"
characters).

Adding countries to the region codelist
---------------------------------------

By setting *definitions.region.country* as *true* in the configuration file:

.. code:: yaml

  definitions:
    region:
      country: true

the nomenclature package will add all countries to the *region* codelist.

More details on the list of countries can be found here: :ref:`countries`.

Adding NUTS to the region codelist
----------------------------------

By setting *definitions.region.nuts* (optional) in the configuration file:

.. code:: yaml

  definitions:
    region:
      nuts:
        nuts-1: [ AT, BE, CZ ]
        nuts-2: [ AT ]
        nuts-3: true

the nomenclature package will add the selected NUTS regions to the *region* codelist.

In the example above, the package will add: NUTS 1 regions for Austria, Belgium
and Czechia, NUTS 2 regions for Austria, NUTS 3 regions for all EU countries.

More details on the list of NUTS regions can be found here: :ref:`nuts`.

Specify dimensions to be read
-----------------------------

The configuration file offers the possibility to set the dimensions which will be read
by *DataStructureDefinition*, overriding the dimensions from the *definitions*
sub-directories. If no sub-directories exist (e.g.: when importing dimensions
from external repositories), setting dimensions in the configuration file is mandatory.

In the below case we specify *region*, *variable* and *scenario* to be read and used for
validation:

.. code:: yaml

  dimensions:
    - region
    - variable
    - scenario
