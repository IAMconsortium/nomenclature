# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import nomenclature
from datetime import datetime

# -- Project information -----------------------------------------------------

project = "nomenclature"
copyright = f"2021-{datetime.now().year}, IIASA"
author = "Scenario Services team, ECE program, IIASA"

# The short X.Y version.
version = nomenclature.__version__
# The full version, including alpha/beta/rc tags.
release = nomenclature.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "numpydoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_click",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
description = "A Python package for working with IAMC-style scenario data"

html_theme_options = {
    "logo": "iamc-logo.png",
    "logo_name": True,
    "description": description,
    "page_width": "1100px",
    "sidebar_width": "240px",
    "github_button": True,
    "github_user": "iamconsortium",
    "github_repo": "nomenclature",
    "code_bg": "#EEE",
    "note_bg": "#EEE",
    "seealso_bg": "#EEE",
    "admonition_xref_bg": "#EEE",
    "admonition_xref_border": "#444",
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["_templates"]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/", None),
    "pyam": ("https://pyam-iamc.readthedocs.io/en/stable/", None),
}

# Autodoc configuration
autodoc_typehints = "none"

# Prolog for all rst files
rst_prolog = """

.. |br| raw:: html

    <br>

"""
