.. _dir_structure:

Directory structure for definitions and mappings
================================================

This is the directory structure that needs to be in place in order for the validation
and region processing to work:

.. code-block:: bash

   .
   ├── definitions
   │   ├── region
   │   │   ├── ...
   │   │   └── regions.yaml
   │   └── variable
   │       ├── ...
   │       └── variable.yaml
   └── mappings [optional]
       ├── model_a.yaml
       └── ...

The :class:`DataStructureDefinition` reads the codelists from the *definitions* folder.

* Inside the ``definitions/`` directory, each "dimension", in our case ``variable/`` and
  ``region/``, must have its own sub-directory.

* The directories inside the ``definitions/`` folder, in the above example *variable*
  and *region* must match IAMC index names (model, scenario, variable and region). The
  name of the folder determines the index dimension the contained codelists are going to
  be applied to. For example every yaml file in the ``variable/`` is applied to the
  *variable* index dimension.  

* Codelists can be spread across multiple yaml files. When the DataStructureDefinition
  object is initialized all files are combined into a single list. For a more structured
  setup, the index dimension folders (e.g. ``variable/``) can contain  contain
  sub-folders. The constructor of DataStructureDefinition automatically traverses all
  sub-folders and combines all yaml files.
  
The :class:`RegionProcessor` reads the model_mappings from the *mappings* folder. If the
project has no model specific mappings, this folder can also be omitted. In this case
*RegionProcessor* **must not** be used as it would try to read a non-existent directory
causing an error. The *mappings* directory directly contains the model mappings. There
are no special sub-folders required. 
