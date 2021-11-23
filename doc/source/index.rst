**nomenclature**: Working with IAMC-style scenario data
=======================================================

Release v\ |version|.

|license| |python| |black| |pytest| |rtd|

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-black
   :target: https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black

.. |python| image:: https://img.shields.io/badge/python-_3.8_|_3.9-blue?logo=python&logoColor=white
   :target: https://github.com/IAMconsortium/nomenclature

.. |pytest| image:: https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml/badge.svg
   :target: https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml

.. |rtd| image:: https://readthedocs.org/projects/nomenclature-iamc/badge/?version=latest
   :target: https://nomenclature-iamc.readthedocs.io

Overview
========

This package facilitates working with data templates that follow the format developed by
the `Integrated Assessment Modeling Consortium (IAMC) <https://www.iamconsortium.org>`_.
It supports validation of scenario data and region processing, which consists of
renaming and aggregation of model "native regions" to "common regions" used in a project.

Table of Contents
=================

.. toctree::
   :maxdepth: 2

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