.. _how-to:

.. currentmodule:: nomenclature

This guide is intended as a quick instruction for adding a model to comparison project.
It is still recommended to read the detailed instructions under :ref:`model_mapping` and
:ref:`region` in particular.

How to add your model mapping to a project repository
=====================================================

There are two parts to adding a new model mapping. The mapping itself and the easily
forgotten additionally required region definitions. 

As outlined in :ref:`model_mapping` a model mapping holds the information about model
native an aggregation regions, for example:

.. code-block:: yaml

    model: model_a
    native_regions:
      - region_1: model_a|Region 1
      - region_2: model_a|Region 2
      - region_3: model_a|Region 3
    common_regions:
      - World:
        - region_1
        - region_2
        - region_3
      - Common region 1:
        - region_1
        - region_2

``model_a`` reports three regions natively, ``region_1``, ``region_2`` and ``region_3``.
These three are to be renamed to the ``{model}|{region}`` pattern as is common place in
many projects. For the ``common_regions``, there are ``World`` and ``Common region 1``.

If this model mapping would be submitted as a pull request to a project repository, the
:func:`assert_valid_structure` (details can be found here: :ref:`cli`) test that is run
automatically would most likely fail.

The reason for this is that it is required for all regions that will be part of the
processing output according to a model mapping to be defined in the list of regions in
the ``definitions/region/`` folder. 

In case of the example mapping above, regions ``model_a|Region 1, model_a|Region 2,
model_a|Region 3, World`` and ``Common region 1`` must be part of the region
definitions. ``region_1, region_2`` and ``region_3`` are not required since they will
not be part of the processing output as they will be renamed.

In most cases the common regions will already be fined. There will, most likely exist a
file ``defintions/region/regions.yaml`` which contains the project's common regions.

For the model native regions, however, the regions will most likely not exist. Therefore
a new yaml file needs to be added to the same pull request that contains the model
mapping. Per convention the ``definitions/region`` folder usually contains a subfolder
called ``model_native_regions`` which is where all files containing model native region
definitions should be put. The name of the file is not functionally relevant but it is
recommended to use the model name.

In order to make to above example model mapping work and the test run, we would
therefore add a file called ``model_a.yaml`` to
``definitions/region/model_native_regions`` with the following content:

.. code-block:: yaml

    model_a:
      - model_a|Region 1
      - model_a|Region 2
      - model_a|Region 3

assuming ``World`` and ``Common region 1`` are already defined, this should make the
tests pass.
