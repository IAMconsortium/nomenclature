.. _getting-started:

.. currentmodule:: nomenclature

Getting started
===============

The nomenclature package facilitates working with codelists that follow the format
developed by the `Integrated Assessment Modeling Consortium (IAMC)
<https://www.iamconsortium.org>`__. It supports validation of scenario data and region
processing, which consists of renaming of model “native regions” and aggregation to
“common regions” used in a project.

There are two main classes that the user interacts with when using the nomenclature
package, :class:`DataStructureDefinition` and :class:`RegionProcessor`.

A :class:`DataStructureDefinition` contains codelists which define allowed *variables*
(including units) and *regions* to be used in a model comparison or scenario exercise
following the IAMC data format.

A :class:`RegionProcessor` is used to facilitate region processing for model comparison
studies. It holds a list of model specific mappings which define renaming of native
regions and aggregation to common regions.

The top-level function *process()* provides a direct entrypoint to validating scenario
data and applying region processing. Details will be covered in
:ref:`minimum-working-example`. Before that, the required directory structure for
definitions and mappings is discussed. 

.. _dir-structure:

Directory structure for definitions and mappings
------------------------------------------------

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

**Notes**

* The **DataStructureDefinition** will be initialized from the *definitions* folder.

* The **RegionProcessor** will be initialized from the *mappings* folder. If the project
  has no model specific mappings, this folder can also be omitted. In this case
  *RegionProcessor* **must not** be used as it would try to read a non-existent
  directory causing an error.

* Inside the *definitions* directory, each "dimension", in our case *variable* and
  *region*, must live in its own sub-directory.

* The directories inside the *definitions* folder, *variable* and *region* are special
  names that must be kept.

* The definitions can be spread across multiple yaml files. In the interest of keeping
  this example minimal only one file for regions and variables is shown.

* The *mappings* directory directly contains the model mappings. There are no special
  sub-folders required. 


.. _minimum-working-example:

Minimum working example
-----------------------

This section aims to provide a minimum working example of how to use the nomenclature
package. It is assumed that the variable templates and model mappings already exist.
Details on how those are structured and how to start using nomenclature "from scratch"
can be found here :ref:`usage`. 

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

**Notes**

* The function :func:`process` takes a :class:`pyam.IamDataFrame` as input.

* :class:`DataStructureDefinition` and :class:`RegionProcessor` are initialized from
  directories containing yaml files. See :ref:`dir-structure` for details.

* The processor argument of :func:`process` is optional and may only to be used if there
  are model mappings. See :ref:`toplevel-functions` for details.

* If not all dimensions of the :class:`DataStructureDefinition` should be validated, a
  *dimensions* argument in form of a list of strings can be provided. Only the provided
  dimensions will then be validated. See :ref:`toplevel-functions` for details.
