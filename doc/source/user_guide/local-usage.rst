.. _local_usage:

Local usage of a project
========================

This section aims to provide a minimum working example of how to use the nomenclature
package.

It is assumed that the variable templates and model mappings already exist. Details on
how those are structured and how to start using nomenclature "from scratch" can be found
in :ref:`codelist` and :ref:`model_mapping` respectively. 

The following outlines how to use the nomenclature package:

.. code-block:: python

  # Import the necessary libraries
  import pyam
  from nomenclature import DataStructureDefinition, RegionProcessor, process
  
  # Initialize DataStructureDefinition from a suitable directory
  dsd = DataStructureDefinition("definitions")
  
  # Initialize a RegionProcessor from a suitable directory that has the mappings
  rp = RegionProcessor.from_directory("mappings")
  
  # Read the data using pyam
  df = pyam.IamDataFrame("/path/to/file")
  
  # Perform the validation and apply the region aggregation
  df = process(df, dsd, processor=rp)

* The function :func:`process` takes a :class:`pyam.IamDataFrame` as input.

* :class:`DataStructureDefinition` and :class:`RegionProcessor` are initialized from
  directories containing yaml files. See :ref:`dir_structure` for details.

* The processor argument of :func:`process` is optional and may only to be used if there
  are model mappings. See :ref:`toplevel_functions` for details.

* Per default :class:`DataStructureDefinition` will search for a ``variable/`` and a
  ``region/`` directory with the corresponding codelists to validate those two
  dimensions. If any another list of dimensions should be validated instead, the
  *dimensions* argument which is a list of strings can be provided. See
  :ref:`toplevel_functions` for details.
