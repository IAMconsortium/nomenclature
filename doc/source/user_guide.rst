.. _user_guide:

.. currentmodule:: nomenclature


User Guide
==========

Typically, nomenclature is used as part of the data upload process for integrated
assessment model comparison studies that use the IIASA Scenario Explorer infrastructure.

As part of the data processing workflow, nomenclature is used to perform two tasks,
input data validation against codelists and region aggregation based on information
given in model mappings.

The three parts of the processing workflow: codelists, model mappings and the actual
processing code are usually hosted in a GitHub repository.

As an example, in the openENTRANCE project (`github.com/openENTRANCE/openentrance
<https://github.com/openENTRANCE/openentrance>`_) these three parts are the
``definitions/`` and ``mappings/`` folders which contain codelists and model mappings,
and ``workflow.py`` which contains the processing code using nomenclature.

The validation and region-processing for a specific can be run locally by any user. In
order to do so, the corresponding GitHub repository needs to be cloned, nomenclature
installed and the ``main`` function in ``workflow.py`` be given a
:class:`pyam.IamDataFrame` of the model data as input.

When working with nomenclature, there are two main classes that the user interacts with,
:class:`DataStructureDefinition` and :class:`RegionProcessor`.

The :class:`DataStructureDefinition` class parses :ref:`codelist` files which define
allowed values, most commonly for *variables* and *regions*, to be used in a model
comparison or scenario exercise.

The :class:`RegionProcessor` parses :ref:`model mapping <model_mapping>` files which
define the renaming of native regions and aggregation to common regions.

The top-level function :func:`process` takes both of the above classes as input along
with data in form of a :class:`pyam.IamDataFrame`. The input data is aggregated using
the RegionProcessor and validated using DataStructureDefinition.

.. toctree::
  :maxdepth: 3

  user_guide/directory-structure
  user_guide/codelist
  user_guide/variable-guidelines
  user_guide/model-mapping
  user_guide/local-usage
