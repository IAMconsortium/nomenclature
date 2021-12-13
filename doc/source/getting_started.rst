.. _getting-started:

Getting started
===============

The nomenclature package facilitates working with data templates that follow the format
developed by the `Integrated Assessment Modeling Consortium (IAMC)
<https://www.iamconsortium.org>`__. It supports validation of scenario data and region
processing, which consists of renaming and aggregation of model “native regions” to
“common regions” used in a project.

There are two main classes that the user interacts with when using the nomenclature
package, **DataStructureDefinition** and **RegionProcessor**. Additionally, there are a
number of auxiliary classes which are used by the two main ones to facilitate validation
and region processing, the two most important ones being **CodeList** and
**RegionAggregationMapping** (a full list of all classes can be found in :ref:`api`).

A **DataStructureDefinition** contains **CodeLists** for *variables* (including units)
and *regions* to be used in a model comparison or scenario exercise following the IAMC
data format.

A **RegionProcessor** holds a list of RegionAggregationMappings and a
DataStructureDefinition. This class is used to facilitate region processing for model
comparison studies.

A **CodeList** is a list of "allowed terms" (or codes), where each term can have several
attributes (e.g., description, unit, parent region).

A **RegionAggregationMapping** is a mapping that defines on a per-model basis how model
native regions should be renamed and aggregated to comparison regions.

In order to reduce the amount of code required, there is a convenience function called
*process* which takes a **DataStructureDefinition** and a **RegionProcessor** as input.
Details will be covered in :ref:`minimum-working-example`. Before this can be explained,
however, the required directory structure for definitions and mappings needs to be
discussed. 

.. _dir-structure:

Directory structure for definitions and mappings
------------------------------------------------

This is the directory structure that needs to be in place in order for the validation and region processing to work:

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
  has no model specific mappings, this folder can also be omitted. In this case,
  however, *RegionProcessor* **must not** be used as it would try to read a non-existent
  directory causing the program to crash.

* Inside the *definitions* directory each "dimension", in our case *variable* and
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
  
  # Initialize DataStructureDefinition and RegionProcessor giving them the
  # directories where the codelists and mappings are defined as input.
  dsd = DataStructureDefinition("definitions/")
  
  # Only to be used if there are mappings!
  rp = RegionProcessor.from_directory("mappings/", dsd)
  
  # Read the data using pyam
  iam_results_file = "some file"
  df = pyam.IamDataFrame(iam_results_file)
  
  # Using the process function we perform the validation of allowed regions and
  # variables as well as the aggregation (if applicable) in one step.
  df = process(df, dsd, processor=rp)

**Notes**

* The pyam library is required as *process* takes a *pyam.IamDataFrame* as input.

* *DataStructureDefinition* and *RegionProcessor* are initialized from directories
  containing yaml files. See :ref:`dir-structure` for details. 

* The processor argument of *process* is optional and may only to be used if there are  
  model mappings. See :ref:`process-function` for details.

* If not all dimensions of the **DataStructureDefinition** should be validated, a
  *dimensions* argument in form of a list of strings can be provided. Only the provided dimensions will then be validated. See :ref:`process-function` for details.
