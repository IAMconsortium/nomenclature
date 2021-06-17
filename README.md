# nomenclature - Working with IAMC-style data templates

Copyright 2021 IIASA

This repository is licensed under the Apache License, Version 2.0 (the "License");  
see the [LICENSE](LICENSE) for details. 

[![license](https://img.shields.io/badge/License-Apache%202.0-black)](https://github.com/IAMconsortium/nomenclature/blob/main/LICENSE)
[![python](https://img.shields.io/badge/python-3.7_|_3.8_|_3.9-blue?logo=python&logoColor=white)](https://github.com/IAMconsortium/pyam)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview

This package facilitates working with data templates that follow the format developed by
the [Integrated Assessment Modeling Consortium (IAMC)](https://www.iamconsortium.org).

## The pyam package

<img src="./_static/pyam-logo.png" width="133" height="100" align="right" alt="pyam logo" />

This package is intended to complement the Python package **pyam**,
an open-source community toolbox for analysis & visualization of scenario data.
That package was developed to facilitate working with timeseries scenario data
conforming to the format developed by the IAMC .
It is used in ongoing assessments by the IPCC and in many model comparison
projects at the global and national level, including several Horizon 2020 projects.

[Read the docs](https://pyam-iamc.readthedocs.io) for more information!

## Getting started

To install this package, please install Python version 3.7 or higher. Then,
download or git-clone this repository and run the following command in the root folder:

```
pip install --editable .
```

Then, open a Python console and import a suitable nomenclature structure from a folder
and run the following code to inspect the variables defined in the nomenclature.

```python
import nomenclature
nc = nomenclature.Nomenclature()
nc.variable
```

## Acknowledgement

<img src="./_static/open_entrance-logo.png" width="202" height="129" align="right" alt="openENTRANCE logo" />

This package is based on the work initially done in the
[Horizon 2020 openENTRANCE](https://openentrance.eu) project, which aims to  develop,
use and disseminate an open, transparent and integrated  modelling platform
for assessing low-carbon transition pathways in Europe.

Refer to the [openENTRANCE/nomenclature](https://github.com/openENTRANCE/nomenclature)
repository for more information.

<img src="./_static/EU-logo-300x201.jpg" width="80" height="54" align="left" alt="EU logo" />
This project has received funding from the European Union’s Horizon 2020 research
and innovation programme under grant agreement No. 835896.
