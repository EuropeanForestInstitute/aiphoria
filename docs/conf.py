# Configuration file for the Sphinx documentation builder.

import datetime

# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'aiphoria dMFA'
author = "Cleo Orfanidou"
copyright = datetime.date.today().strftime("%Y") + " aiphoria developers"
version: str = "latest"  # required by the version switcher

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


master_doc = "index"

root_doc = "index"
html_static_path = ["_static"]
templates_path = ["_templates"]
exclude_patterns = ["_build"]

extensions = [
    # Your existing extensions
    ...,
    "myst_parser",
]
