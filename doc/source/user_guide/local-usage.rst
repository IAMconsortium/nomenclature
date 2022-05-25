.. _local_usage:

.. currentmodule:: nomenclature

Local usage of a project
========================

.. attention:: This page is intended for users who are familiar with Python,
    `git <https://git-scm.com>`_  and a service like `GitHub <https://github.com>`_.

You can use the **nomenclature** package locally (on your machine) for validation
and region-aggregration. This can be helpful as part of processing your model results,
or to ensure that a submission to an IIASA Scenario Explorer instance will succeed.

Requirements
------------

1. Install the **nomenclature** package (see the :ref:`installation` instructions)
2. Have a project folder that has the required :ref:`dir_structure`:

   * Set up the folder with the required structure and files yourself, or
   * Clone the git repository for a specific project
     (e.g., `openENTRANCE <https://github.com/openENTRANCE/openentrance>`_)

   .. attention:: When using a project repository from GitHub or a similar service,
          make sure that you keep your local clone in sync with the upstream repository.

Usage options
-------------

Validation against the codelists
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The easiest use case is to validate that a data file or an
:class:`IamDataFrame <pyam.IamDataFrame>` is compatible with the codelists
(lists of variables and regions) of a project's :class:`DataStructureDefinition`.

If there are inconsistencies with the codelists, the method
:meth:`validate <DataStructureDefinition.validate>` will raise an error.
If the scenario data is consistent, the method returns *True*.

.. code-block:: python

  import pyam
  from nomenclature import DataStructureDefinition, process

  # Initialize the DataStructureDefinition from a suitable directory
  dsd = DataStructureDefinition("definitions")

  # Read the data using pyam
  df = pyam.IamDataFrame("/path/to/file")

  # Perform the validation
  dsd.validate(df)

Validation and region processing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A more elaborate use case is to perform validation against the codelists and use the
:class:`RegionProcessor` to aggregate timeseries from "native regions" of a model to
"common regions" (i.e., regions that are used for scenario comparison in a project).

.. code-block:: python

  # Import the necessary libraries
  import pyam
  from nomenclature import DataStructureDefinition, RegionProcessor, process
  
  # Initialize a DataStructureDefinition from a suitable directory
  dsd = DataStructureDefinition("definitions")
  
  # Initialize a RegionProcessor from a suitable directory that has the mappings
  rp = RegionProcessor.from_directory("mappings")
  
  # Read the data using pyam
  df = pyam.IamDataFrame("/path/to/file")
  
  # Perform the validation and apply the region aggregation
  df = process(df, dsd, processor=rp)

Refer to the section :ref:`model_mapping` for more information about this feature.

Using a project-specific workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Several projects specify custom workflows that combine validation and region-processing
with other validation steps or post-processing modules. These workflows are usually
implemented as a ``main()`` function in ``workflow.py`` of a project repository.

.. attention:: The working-directory of the Python console has to be set to the clone
     of the project repository.

.. code-block:: python

  # Import the pyam library and the project-specific workflow
  import pyam
  from workflow import main as project_workflow

  # Read the scenario data and call the project-specific workflow
  df = pyam.IamDataFrame("/path/to/file")
  df = project_workflow(df)
