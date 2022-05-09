.. _getting_started:

.. currentmodule:: nomenclature


Getting started
===============

Package overview
----------------

The nomenclature package facilitates working with "codelists" that follow a format
developed by the `Integrated Assessment Modeling Consortium (IAMC)
<https://www.iamconsortium.org>`__, detailed here :ref:`codelist`.

Codelists are yaml files that specify allowed values for variables, regions or scenarios
for a model comparison project. Nomenclature parses these files and checks if provided
model results are compliant with the specifications.

Additionally, nomenclature can perform "region processing". Region processing consists
of renaming of model “native regions” and aggregation of model native results to “common
regions”. This enables comparison across different models on the same regional
resolution. This processing is defined on a per-model basis in yaml files which are
called "model mappings". Details on the format can be found here :ref:`model_mapping`.

Installation
------------

.. attention:: The nomenclature requires python >= 3.8


Via Pip
^^^^^^^
.. attention::  The nomenclature package is distributed as "nomenclature-iamc" on pypi.

.. code-block:: bash

    pip install nomenclature-iamc


From Source
^^^^^^^^^^^

nomenclature can also be installed from source. This will get you the latest version
of the main branch.

.. code-block:: bash

    pip install -e git+https://github.com/IAMconsortium/nomenclature@main#egg=nomenclature


Standard use case
-----------------

Typically, nomenclature is used as part of the data upload process for integrated
assessment model comparison studies that use the IIASA Scenario Explorer infrastructure.

The three parts of the processing workflow: codelists, model mappings and the workflow
code are usually hosted in a GitHub repository. As an example, in the openENTRANCE
project (`github.com/openENTRANCE/openentrance
<https://github.com/openENTRANCE/openentrance>`_) these three parts are the
``definitions/`` and ``mappings/`` folders which contain codelists and model mappings
respectively and ``workflow.py`` which contains the processing code using nomenclature.

The validation and region-processing for a specific can be run locally by any user. In
order to do so, the corresponding GitHub repository needs to be cloned, nomenclature
installed and the ``main`` function in ``workflow.py`` be given a
:class:`pyam.IamDataFrame` of the model data as input.


Command line interface
----------------------

Nomenclature offers CLI (=command line interface) functionality that validates codelists
and model mappings *themselves* (as opposed to input data). This can be very useful to
ensure that all codelists or model mappings for a project are understood by
nomenclature:

.. code-block:: bash

  nomenclature validate-project /folder/where/definitions/and/mappings/are

