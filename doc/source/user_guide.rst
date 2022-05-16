.. _user_guide:

.. currentmodule:: nomenclature


User Guide
==========

There are two main classes that the user interacts with when using the nomenclature
package, :class:`DataStructureDefinition` and :class:`RegionProcessor`.

The :class:`DataStructureDefinition` class parses :ref:`codelist` files which define
allowed values, most commonly for *variables* and *regions*, to be used in a model
comparison or scenario exercise.

The :class:`RegionProcessor` parses :ref:`model mapping <model_mapping>` files which
define the renaming of native regions and aggregation to common regions.

The top-level function *process()* takes both of the above classes as input along with
data in form of a :class:`pyam.IamDataFrame`. The input data is aggregated using the
RegionProcessor and validated using DataStructureDefinition. Details are covered in
:ref:`minimum_working_example`. 

Before that, however, the required directory structure for definitions and mappings as
well as the file specifications for codelists and model mappings are discussed. 

.. toctree::
  :maxdepth: 3

  user_guide/directory-structure
  user_guide/codelist
  user_guide/model-mapping
  user_guide/code-example
  user_guide/region-processing
  user_guide/cli
