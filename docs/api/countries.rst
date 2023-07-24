.. _countries:

.. currentmodule:: nomenclature.countries

A common list of countries
==========================

Having an agreed list of country names including a mapping to alpha-3 and alpha-2 codes
(also know as ISO3 and ISO2 codes) is an important prerequisite for scenario analysis
and model comparison.

The :class:`nomenclature` package builds on the :class:`pycountry` package
(`link <https://github.com/flyingcircusio/pycountry>`_) to provide a utility for country
names based on the ISO 3166-1 standard.

For consistency with established conventions in the modelling community, several country
names are shortened compared to ISO 3166-1, e.g. from "Bolivia, Plurinational State of"
to "Bolivia". Also, "Kosovo" is added even though it is not a universally recognized
state. See the full list of changes on GitHub_.

You can access the list of countries via the model registration `Excel template`_.

You can also use this utility for mapping between country names as used in the community
and alpha-3 or alpha-2 codes, as shown in this example.

.. _GitHub: https://github.com/IAMconsortium/nomenclature/blob/main/nomenclature/countries.py

.. _`Excel template`: https://raw.githubusercontent.com/IAMconsortium/nomenclature/main/templates/model-registration-template.xlsx

.. code:: python

  from nomenclature import countries

  name = countries.get(alpha_3="...").name
  alpha_3 = countries.get(name="...").alpha_3
  alpha_2 = countries.get(name="...").alpha_2

.. autoclass:: Countries
   :members: get
