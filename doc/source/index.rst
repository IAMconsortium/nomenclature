.. currentmodule:: nomenclature

**nomenclature**: Working with IAMC-format project templates
===========================================================

Release v\ |version|.

|license| |doi| |python| |black| |pytest| |rtd|

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-black
   :target: https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE

.. |doi| image:: https://zenodo.org/badge/375724610.svg
   :target: https://zenodo.org/badge/latestdoi/375724610

.. |python| image:: https://img.shields.io/badge/python-_3.8_|_3.9_|_3.10-blue?logo=python&logoColor=white
   :target: https://github.com/IAMconsortium/nomenclature

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. |pytest| image:: https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml/badge.svg
   :target: https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml

.. |rtd| image:: https://readthedocs.org/projects/nomenclature-iamc/badge/?version=latest
   :target: https://nomenclature-iamc.readthedocs.io

Overview
--------

The **nomenclature** package facilitates validation and processing of scenario data
for model comparison projects and scenario analysis. It allows to manage
project templates and "codelists" that follow the format developed by the
`Integrated Assessment Modeling Consortium (IAMC) <https://www.iamconsortium.org>`_.

A "codelist" is a list allowed values (or "codes") for dimensions of IAMC-format data,
typically *regions* and *variables*. Each code can have additional attributes:
for example, a "variable" (string) usually has a definition and an expected unit.
Read the `SDMX Guidelines <https://sdmx.org/?page_id=4345>`_ for more information on
the concept of codelists.

The **nomenclature** package supports three main use cases:

- Management of codelists, definitions and mappings for model comparison projects
- Validation of scenario data against the codelists of a specific project
- Region-processing (aggregation and renaming) from "native regions" of a model to
  "common regions" (i.e., regions that are used for scenario comparison in a project).

The codelists, definitions and mappings are stored as yaml files.
Refer to the :ref:`user_guide` for more information.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   installation
   user_guide
   api
   cli

Acknowledgement
---------------

.. figure:: _static/open_entrance-logo.png
   :align: right

This package is based on the work initially done in the Horizon 2020 project
`openENTRANCE <https://openentrance.eu>`_, which aims to  develop, use and
disseminate an open, transparent and integrated  modelling platform for assessing
low-carbon transition pathways in Europe.

Refer to the `openENTRANCE/openentrance`_ repository on GitHub for more information.

.. _`openENTRANCE/openentrance` : https://github.com/openENTRANCE/openentrance

.. figure:: _static/EU-logo-300x201.jpg
   :align: left
   :width: 80px

|br| This project has received funding from the European Union’s Horizon 2020
research and innovation programme under grant agreement No. 835896.
