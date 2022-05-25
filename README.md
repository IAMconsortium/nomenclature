# nomenclature - Working with IAMC-format project templates

Copyright 2021-2022 IIASA

This repository is licensed under the Apache License, Version 2.0 (the "License"); see
the [LICENSE](LICENSE) for details.

[![license](https://img.shields.io/badge/License-Apache%202.0-black)](https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/375724610.svg)](https://zenodo.org/badge/latestdoi/375724610)
[![python](https://img.shields.io/badge/python-3.8_|_3.9_|_3.10-blue?logo=python&logoColor=white)](https://github.com/IAMconsortium/nomenclature)
[![Code style:
black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pytest](https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml/badge.svg)](https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml)
[![ReadTheDocs](https://readthedocs.org/projects/docs/badge)](https://nomenclature-iamc.readthedocs.io)

## Overview

The **nomenclature** package facilitates validation and processing of scenario data
for model comparison projects and scenario analysis. It allows to manage
project templates and "codelists" that follow the format developed by the
[Integrated Assessment Modeling Consortium (IAMC)](https://www.iamconsortium.org)..

A "codelist" is a list allowed values (or "codes") for dimensions of IAMC-format data,
typically *regions* and *variables*. Each code can have additional attributes:
for example, a "variable" (string) usually has a definition and an expected unit.
Read the [SDMX Guidelines](https://sdmx.org/?page_id=4345) for more information on
the concept of codelists.

The **nomenclature** package supports three main use cases:

- Management of codelists, definitions and mappings for model comparison projects
- Validation of scenario data against the codelists of a specific project
- Region-processing (aggregation and renaming) from "native regions" of a model to
  "common regions" (i.e., regions that are used for scenario comparison in a project).
  
The full documentation is hosted on [Read the
Docs](https://nomenclature-iamc.readthedocs.io/)

## The pyam package

<img src="https://github.com/IAMconsortium/pyam/blob/main/doc/logos/pyam-logo.png"
width="133" height="100" align="right" alt="pyam logo" />

This package is intended to complement the Python package **pyam**, an open-source
community toolbox for analysis & visualization of scenario data. That package was
developed to facilitate working with timeseries scenario data conforming to the format
developed by the IAMC. It is used in ongoing assessments by the IPCC and in many model
comparison projects at the global and national level, including several Horizon 2020
projects.

[Read the Docs](https://pyam-iamc.readthedocs.io) for more information!

## Getting started

To install the latest release of the package, please use the following command:

```bash
pip install nomenclature-iamc
```

Alternatively, it can also be installed directly from source:

```bash
pip install -e git+https://github.com/IAMconsortium/nomenclature#egg=nomenclature
```

See the [User Guide](https://nomenclature-iamc.readthedocs.io/en/latest/user_guide.html)
for the main use cases of this package.

## Acknowledgement

<img src="./doc/source/_static/open_entrance-logo.png" width="202" height="129"
align="right" alt="openENTRANCE logo" />

This package is based on the work initially done in the [Horizon 2020
openENTRANCE](https://openentrance.eu) project, which aims to  develop, use and
disseminate an open, transparent and integrated  modelling platform for assessing
low-carbon transition pathways in Europe.

Refer to the [openENTRANCE/nomenclature](https://github.com/openENTRANCE/nomenclature)
repository for more information.

<img src="./doc/source/_static/EU-logo-300x201.jpg" width="80" height="54" align="left"
alt="EU logo" /> This project has received funding from the European Union’s Horizon
2020 research and innovation programme under grant agreement No. 835896.
