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

needs_sphinx = "7.3.0"

extensions = [
    # core extensions
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    # Markdown support
    # 'myst_parser', # do not enable separately if using myst_nb, compare: https://github.com/executablebooks/MyST-NB/issues/421#issuecomment-1164427544
    # Jupyter Notebook support
    "myst_nb",
    # mermaid support
    "sphinxcontrib.mermaid",
    # API documentation support
    "autoapi",
    # responsive web component support
    "sphinx_design",
    # custom 404 page
    "notfound.extension",
    # custom favicons
    "sphinx_favicon",
    # copy button on code blocks
    "sphinx_copybutton",
    # carousels
    "sphinx_carousel.carousel",
]
