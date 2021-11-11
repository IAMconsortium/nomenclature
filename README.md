# nomenclature - Working with IAMC-style data templates

Copyright 2021 IIASA

This repository is licensed under the Apache License, Version 2.0 (the "License"); see
the [LICENSE](LICENSE) for details.

[![license](https://img.shields.io/badge/License-Apache%202.0-black)](https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE)
[![python](https://img.shields.io/badge/python-3.7_|_3.8_|_3.9-blue?logo=python&logoColor=white)](https://github.com/IAMconsortium/nomenclature)
[![Code style:
black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

This package facilitates working with data templates that follow the format developed by
the [Integrated Assessment Modeling Consortium (IAMC)](https://www.iamconsortium.org).
It supports validation of scenario data and region processing, which consists of
renaming and aggregation of model "native regions" to "common regions" used in a
project.

A **DataStructureDefinition** class contains **CodeLists** for *variables* (including
units) and *regions* to be used in a model comparison or scenario exercise following the
IAMC data format.

A **CodeList** is a list of "allowed terms" (or codes), where each term can have several
attributes (e.g., description, unit, parent region).

A **RegionAggregationMapping** is a mapping that defines on a per-model basis how model
native regions should be renamed and aggregated to comparison regions.

A **RegionProcessor** is a class that holds a list of RegionAggregationMappings and a
DataStructureDefinition. This class is used to facilitate region processing for model
comparison studies.

## The structure of a datastructure definition

A **DataStructureDefinition** is initialized from a folder with the following structure:

### Variables

The *variable* codelist of the **DataStructureDefinition** will be read from all yaml
files located  in a folder of that name (including any sub-folders). They must be
formatted as a list of dictionaries mapping the variable (key) to its attributes.

```yaml
- Some Variable:
    description: A short description
    unit: A unit
    <other attribute>: Some text (optional)
```

Every variable must have a **unit**, which should be compatible with the Python package
[iam-units](https://github.com/iamconsortium/units). The unit attribute can be empty,
i.e., the variable is *dimensionless*.

#### Tags

To avoid repetition (and subsequent errors), any number of yaml files can be used as
"tags" using a nested list of dictionaries. The files defining the tags must have a name
starting with `tag_`.

```yaml
- <Tag>:
  - Some Key:
      description: a short description of the key
```

When importing the codelist, any occurrence of `<Tag>` in a variable name will be
replaced by every element in the Tag dictionary. The `<Tag>` will also be replaced in
any of the variable attributes.

There must be only one top-level entry in any yaml file to be used as tag.

## Model Mappings

Model mappings, defined in a .yaml format serve three different purposes on a per-model
basis:

1. Define a list of model native regions that are to be selected (and usually uploaded)
   from an IAM result. This also serves as an implicit exclusion list for model native
   regions, since only explicitly mentioned regions are selected.

2. Allow for renaming of model native regions.

3. Define how model native regions should be aggregated to common regions.

This example illustrates how such a model mapping looks like:

```yaml
model: model_a
native_regions:
  - region_a: alternative_name_a
  - region_b
common_regions:
  - common_region_1:
    - region_a
    - region_b
  - common_region_2:
    - ...
```

### Notes

* The names of the three top level keywords `model`, `native_regions` and
  `common_regions` are fixed.
* Required properties are `model` and **at least** either `native_regions` or
  `common_regions`. **Both** are **allowed** as well.
* **`model`** (str): specifies the model name for which the mapping applies.
* **`native_regions`** (list): list of model native regions serves as a selection as to
  which regions to keep.
  * In the above example `region_a` is to be renamed to `alternative_name_a`. This is
    done by defining a key-value pair of `model_native_name: new_name`.
  * `region_b` is selected but the name is not changed.
  * Assuming `model_a` also defines a third region `region_c`, since it is not mentioned
    it will be **dropped** from the data.
* **`common_regions`** (list): list of common regions which will be computed as
  aggregates. They are defined as list entries which themselves have a list of
  constituent regions. These constituent regions must be model native regions.
  * **Important to note** the names of the constituent regions **must** refer to the
    **original** model native region names. In the above example `region_a` and
    `region_b` and **not** `alternative_name_a`.

#### Guidelines and naming convention

The variable name (code) should adhere to the following conventions:

- A `|` (pipe) character indicates levels of hierarchy
- Do not use spaces before and after the `|` character, but add a space between words
  (e.g., `Primary Energy|Non-Biomass Renewables`)
- All words must be capitalised (except for 'and', 'w/', 'w/o', etc.)
- Do not use abbreviations (e.g, 'PHEV') unless strictly necessary
- Add hierarchy levels where it might be useful in the future, e.g., use `Electric
  Vehicle|Plugin-Hybrid` instead of 'Plugin-Hybrid Electric Vehicle'
- Do not use abbreviations of statistical operations ('min', 'max', 'avg') but always
  spell out the word
- Do not include words like 'Level' or 'Quantity' in the variable, because this should
  be clear from the context or unit

### Regions

The *region* codelist of the nomenclature will be read from all yaml files located in a
folder of that name (including any sub-folders). To avoid repeating a "hierarchy"
attribute many times (e.g., country, continent), the yaml files must have a nested
dictionary structure:

```yaml
- <Hierarchy Level>:
  - Region Name:
      Attribute: Attribute value
```

When importing the codelist, the hierarchy will be added as attribute, such that it can
be retrieved as

```python
DataStructureDefinition.region["Region Name"]["Hierarchy"] = "<Hierarchy Level>"
```

Other attributes specified in the yaml file can include (for countries) ISO2/3-codes, or
the list of countries included in a macro-region (i.e., a continent or large region).

## The pyam package

<img src="./_static/pyam-logo.png" width="133" height="100" align="right" alt="pyam
logo" />

This package is intended to complement the Python package **pyam**, an open-source
community toolbox for analysis & visualization of scenario data. That package was
developed to facilitate working with timeseries scenario data conforming to the format
developed by the IAMC . It is used in ongoing assessments by the IPCC and in many model
comparison projects at the global and national level, including several Horizon 2020
projects.

[Read the docs](https://pyam-iamc.readthedocs.io) for more information!

## Getting started

To install this package, please install Python version 3.7 or higher. Then, download or
git-clone this repository and run the following command in the root folder:

```
pip install --editable .
```

Then, open a Python console and import a suitable nomenclature structure from a folder
and run the following code to inspect the variables defined in the nomenclature.

```python
import nomenclature
project = nomenclature.DataStructureDefinition("path/to/definition/folder")
project.variable
```

## Acknowledgement

<img src="./_static/open_entrance-logo.png" width="202" height="129" align="right"
alt="openENTRANCE logo" />

This package is based on the work initially done in the [Horizon 2020
openENTRANCE](https://openentrance.eu) project, which aims to  develop, use and
disseminate an open, transparent and integrated  modelling platform for assessing
low-carbon transition pathways in Europe.

Refer to the [openENTRANCE/nomenclature](https://github.com/openENTRANCE/nomenclature)
repository for more information.

<img src="./_static/EU-logo-300x201.jpg" width="80" height="54" align="left" alt="EU
logo" /> This project has received funding from the European Union’s Horizon 2020
research and innovation programme under grant agreement No. 835896.
