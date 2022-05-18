.. currentmodule:: nomenclature

**nomenclature**: Working with IAMC-style scenario data
=======================================================

Release v\ |version|.

|license| |python| |black| |pytest| |rtd|

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-black
   :target: https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. |python| image:: https://img.shields.io/badge/python-_3.8_|_3.9_|_3.10-blue?logo=python&logoColor=white
   :target: https://github.com/IAMconsortium/nomenclature

.. |pytest| image:: https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml/badge.svg
   :target: https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml

.. |rtd| image:: https://readthedocs.org/projects/nomenclature-iamc/badge/?version=latest
   :target: https://nomenclature-iamc.readthedocs.io

Overview
========

The nomenclature package facilitates working with "codelists" that follow the format
developed by the `Integrated Assessment Modeling Consortium (IAMC)
<https://www.iamconsortium.org>`_. Codelists are yaml file based lists of allowed values
(or codes) for dimensions of IAMC-style data, for example *regions* and *variables*.
Using these codelists, nomenclature performs data validation to check if a provided data
set conforms to the values in the code lists. 

Additionally, it can execute "region processing", which consists of renaming of "native
regions" and/or aggregation to "common regions" used in a project.

Those two tasks are carried out by two classes:

#. The :class:`DataStructureDefinition` class handles the validation of scenario data.
   It contains data templates for *variables* (including units) and *regions* to be used
   in a model comparison or scenario exercise following the IAMC data format.

#. The :class:`RegionProcessor` class carries out renaming and aggregation based on
   information given in yaml model mapping files.

Instructions on how to install nomenclature can be found in the "Installation" section.

The complete user guide including the file specifications for codelists and model
mappings, example code and details on how to use nomenclature is given in "User Guide".

Table of Contents
=================

.. toctree::
   :maxdepth: 3

   installation
   user_guide
   api

Acknowledgement
===============

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
