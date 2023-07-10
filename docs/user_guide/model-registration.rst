.. _model-registration:

.. currentmodule:: nomenclature

Model registration
==================

This guide presents instructions for "registering a model" for a project.

Model registration for a **nomenclature**-based project requires two specifications:

* | a list of region names as they should appear in the processed scenario data
  | (e.g., after processing as part of the upload to a *Scenario Explorer* instance)
* a model mapping to perform region aggregation from *native_regions* to
  *common_regions* and renaming of model native regions (optional)

Please read the detailed explanations of :ref:`region` and :ref:`model_mapping` before
proceeding with model registration.

Option 1) Registration using an Excel template
----------------------------------------------

Please use the `Excel template`_ and send it to the project managers by email.

.. _`Excel template`: https://raw.githubusercontent.com/IAMconsortium/nomenclature/main/templates/model-registration-template.xlsx

Option 2) Registration using a GitHub pull request
--------------------------------------------------

The preferred approach for model registration is starting a GitHub pull request.
Please contact the administrators if permissions for the project repository
are required.

A model-registration pull request adds the following files (if required).

Native-region definitions
^^^^^^^^^^^^^^^^^^^^^^^^^

If the model reports results at a model-specific regional resolution (e.g., other than
national countries), add a file ``<your-model_vX.X>.yaml`` in the folder
``definitions/region/model_native_regions/``.

This file should follow the region-naming conventions of :ref:`region`.
The *hierarchy* property should be the model name inluding the version number.

Model mapping for region processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the scenario-processing workflow should execute a region-processing step,
add a file ``<your-model_vX.X>.yaml`` in the folder ``mappings/``.

This file should follow the region-naming conventions of :ref:`model_mapping`.

Continuous integration
^^^^^^^^^^^^^^^^^^^^^^

When registering a model via a pull request to a GitHub project repository, a
GitHub Actions workflow is executed for ensuring that the model mapping is valid.
This serves to ensure that there are no typos or inconsistencies in the mapping or
region names. For example, only regions defined in the *region* codelist can be
used as targets for renaming or aggregation in the region-aggregation.

You can run the validation locally using the function :func:`assert_valid_structure`
of the :ref:`cli`.
