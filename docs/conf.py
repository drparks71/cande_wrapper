import os
import sys

# Add the source tree so autodoc can import without building the Fortran extension
sys.path.insert(0, os.path.abspath("../src"))

project = "cande-wrapper"
copyright = "2025, Dane Parks"
author = "Dane Parks"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_mock_imports = [
    "cande_wrapper._cande",
    "plotly",
]

autodoc_member_order = "bysource"

html_theme = "sphinx_rtd_theme"
