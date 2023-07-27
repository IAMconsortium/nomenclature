.. _config:

.. currentmodule:: nomenclature

Nomenclature configuration
==========================

The nomenclature package features a configuration file that is used to enable the
following features:

* Import codelists from public GitHub repositories
* Add a list of common countries (details: :ref:`countries`) to the region codelist

Configuration file format
-------------------------

The configuration file **must be** located on the same level as the *mappings* and
*definitions* directories.

The file **must be** in yaml format and named *nomenclature.yaml*.

Importing from an external repository
-------------------------------------

In order to import form an external repository the configuration file must define the
repository und the repositories key.

The repository needs a name, in the example below *common-definitions* and a *url*, for
example:

.. code:: yaml

  repositories:
    common-definitions:
      url: https://github.com/IAMconsortium/common-definitions.git/

In order for the import to work the url must be given in the above format, i.e. with the
leading *https://* and the trailing *.git/*.

Information from an external repository can either be used for codelists or model
mappings, or both.

For use in, for example, the *region* and *variable* codelists, the following is
required:

.. code:: yaml

  repositories:
    common-definitions:
      url: https://github.com/IAMconsortium/common-definitions.git/
  definitions:
    region:
      repository: common-definitions
    variable:
      repository: common-definitions

The value in *definitions.region.repository* needs to reference the repository in the
*repositories* section.

Adding a common list of countries to the region codelist
--------------------------------------------------------

By setting *definitions.region.country* as *true* in the configuration file:

.. code:: yaml

  definitions:
    region:
      country: true

the nomenclature package will add a common list of countries to a region codelist.

More details on the list of countries can be found here: :ref:`countries`.
