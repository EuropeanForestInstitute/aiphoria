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
    "sphinx_rtd_theme",
    # Markdown support
    "myst_parser",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = "aiphoria-logo.png"
html_favicon = "favicon.ico" 
html_theme_options = {
    'logo_only': True,
    'display_version': False,
"style_nav_header_background": "#1D5905",
}
