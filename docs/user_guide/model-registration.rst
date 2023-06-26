.. _model-registration:

.. currentmodule:: nomenclature

Model registration
==================

This guide presents a quick instruction for "registering a model" in a project workflow.

It is still recommended to read the detailed instructions under :ref:`model_mapping` and
:ref:`region` in particular.

Region processing
-----------------

"Registering a model" for a **nomenclature**-based project workflow requires two
specifications: 

* a model mapping to perform region aggregation from *native_regions* to
  *common_regions* and renaming of model native regions (optional)
* a list of region names as they should appear in the processed scenario data

Model mapping
^^^^^^^^^^^^^

For this guide we will consider a model mapping as an example:

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

*For more details on the model-native and common regions refer to*
:ref:`native-vs-common-region`.

Region definitions
^^^^^^^^^^^^^^^^^^

In order to constitute a valid "model registration", regions ``model_a|Region 1``,
``model_a|Region 2``, ``model_a|Region 3``, ``World`` and ``Common region 1`` **must**
be part of the region definitions. 

``region_1``, ``region_2`` and ``region_3`` are **not required** since they refer to the
input names of ``model_a``'s regions and will be renamed in the processing.

In most cases, the common regions (in the above example ``World`` and ``Common region
1``) will already be defined in a file called ``definitions/region/regions.yaml``.

The model native regions, however, most likely need to be added. For this, a new yaml
file should be created, usually in ``definitions/region/model_native_regions/``. The
file does not need to have any special name but it is recommended to use the model name.

In order to complete the model registration for the example above, we would therefore
add a file called ``model_a.yaml`` to ``definitions/region/model_native_regions/`` with
the following content:

.. code-block:: yaml

    model_a:
      - model_a|Region 1
      - model_a|Region 2
      - model_a|Region 3

This combination of a model mapping and the definition of all regions that are part of
the processing output constitutes a complete model registration.

Continuous Integration
----------------------

In most cases, a model registration is submitted as a pull request to a project repository hosted on GitHub. As part
of this, :func:`assert_valid_structure` (details can be found here: :ref:`cli`) is run
automatically to ensure that the model registration is valid. Any regions that are, for
example mentioned in a mapping but not defined will raise an error.
