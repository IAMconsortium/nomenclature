# nomenclature - Working with IAMC-format project definitions

Copyright 2021-2023 IIASA

This repository is licensed under the Apache License, Version 2.0 (the "License"); see
the [LICENSE](LICENSE) for details.

[![license](https://img.shields.io/badge/License-Apache%202.0-black)](https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/375724610.svg)](https://zenodo.org/badge/latestdoi/375724610)
[![python](https://img.shields.io/badge/python-≥3.10,<3.14-blue?logo=python&logoColor=white)](https://github.com/IAMconsortium/nomenclature)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pytest](https://img.shields.io/github/actions/workflow/status/iamconsortium/nomenclature/pytest.yml?logo=GitHub&label=pytest)](https://github.com/IAMconsortium/nomenclature/actions/workflows/pytest.yml)
[![ReadTheDocs](https://readthedocs.org/projects/nomenclature-iamc/badge)](https://nomenclature-iamc.readthedocs.io)

## Overview

The **nomenclature** package facilitates validation and processing of scenario data.
It allows managing definitions of data structures for model comparison projects and
scenario analysis studies using the data format developed by the
[Integrated Assessment Modeling Consortium (IAMC)](https://www.iamconsortium.org).

A data structure definition consists of one or several "codelists".
A codelist is a list of allowed values (or "codes") for dimensions of IAMC-format data,
typically *regions* and *variables*. Each code can have additional attributes:
for example, a "variable" has to have an expected unit and usually has a description.
Read the [SDMX Guidelines](https://sdmx.org/?page_id=4345) for more information on
the concept of codelists.

The **nomenclature** package supports three main use cases:

- Management of codelists and mappings for model comparison projects
- Validation of scenario data against the codelists of a specific project
- Processing of scenario results, e.g. aggregation and renaming from "native regions" of
  a model to "common regions" (i.e., regions that are used for scenario comparison in a project).

The documentation is hosted on [Read the Docs](https://nomenclature-iamc.readthedocs.io/).

## Integration with the pyam package

<img src="https://github.com/IAMconsortium/pyam/blob/main/docs/logos/pyam-logo.png"
width="133" height="100" align="right" alt="pyam logo" />

The **nomenclature** package is designed to complement the Python package **pyam**,
an open-source community toolbox for analysis & visualization of scenario data.
The **pyam** package was developed to facilitate working with timeseries scenario data
conforming to the format developed by the IAMC. It is used in ongoing assessments by
the IPCC and in many model comparison projects at the global and national level,
including several Horizon 2020 & Horizon Europe projects.

The validation and processing features of the **nomenclature** package
work with scenario data as a [**pyam.IamDataFrame**](https://pyam-iamc.readthedocs.io/en/stable/api/iamdataframe.html) object.

[Read the **pyam** Docs](https://pyam-iamc.readthedocs.io) for more information!

## Getting started

To install the latest release of the package, please use the following command:

```bash
pip install nomenclature-iamc
```

Alternatively, it can also be installed directly from source:

```bash
pip install -e git+https://github.com/IAMconsortium/nomenclature#egg=nomenclature-iamc
```

See the [User Guide](https://nomenclature-iamc.readthedocs.io/en/latest/user_guide.html)
for the main use cases of this package.

## Acknowledgement

<img src="./docs/_static/open_entrance-logo.png" width="202" height="129"
align="right" alt="openENTRANCE logo" />

This package is based on the work initially done in the [Horizon 2020
openENTRANCE](https://openentrance.eu) project, which aims to  develop, use and
disseminate an open, transparent and integrated  modelling platform for assessing
low-carbon transition pathways in Europe.

Refer to the [openENTRANCE/openentrance](https://github.com/openENTRANCE/openentrance)
repository for more information.

<img src="./docs/_static/EU-logo-300x201.jpg" width="80" height="54" align="left"
alt="EU logo" /> This project has received funding from the European Union’s Horizon
2020 research and innovation programme under grant agreement No. 835896.
