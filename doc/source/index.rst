.. currentmodule:: nomenclature

**nomenclature**: Working with IAMC-format project definitions
==============================================================

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

The **nomenclature** package facilitates validation and processing of scenario data.
It allows to manage definitions of data structures for model comparison projects and
scenario analysis studies using the data format developed by the
`Integrated Assessment Modeling Consortium (IAMC) <https://www.iamconsortium.org>`_.

A data structure definition consists of one or several "codelists".
A codelist is a list of allowed values (or "codes") for dimensions of IAMC-format data,
typically *regions* and *variables*. Each code can have additional attributes:
for example, a "variable" has to have an expected unit and usually has a description.
Read the `SDMX Guidelines <https://sdmx.org/?page_id=4345>`_ for more information on
the concept of codelists.

The **nomenclature** package supports three main use cases:

- Management of codelists and mappings for model comparison projects
- Validation of scenario data against the codelists of a specific project
- Region-processing (aggregation and renaming) from "native regions" of a model to
  "common regions" (i.e., regions that are used for scenario comparison in a project).

The codelists and mappings are stored as yaml files.
Refer to the :ref:`user_guide` for more information.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   installation
   user_guide
   api
   cli

Integration with the **pyam** package
-------------------------------------

.. image:: https://raw.githubusercontent.com/IAMconsortium/pyam/main/doc/logos/pyam-header.png
   :width: 320px
   :align: right
   :target: https://pyam-iamc.readthedocs.io

The **nomenclature** package is designed to complement the Python package **pyam**,
an open-source community toolbox for analysis & visualization of scenario data.
The **pyam** package was developed to facilitate working with timeseries scenario data
conforming to the format developed by the IAMC. It is used in ongoing assessments by
the IPCC and in many model comparison projects at the global and national level,
including several Horizon 2020 & Horizon Europe projects.

The validation and processing features of the **nomenclature** package
work with scenario data as a pyam.IamDataFrame_ object.

`Read the Docs <https://pyam-iamc.readthedocs.io>`_ for more information!

.. _pyam.IamDataFrame : https://pyam-iamc.readthedocs.io/en/stable/api/iamdataframe.html

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
