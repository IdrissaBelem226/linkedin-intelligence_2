import os
import sys
sys.path.insert(0, os.path.abspath("../.."))

project = "audience_enrichment"
author = "Detralytics"
release = "0.1.0"
copyright = "2026, Detralytics"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

autosummary_generate = True
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "titles_only": False,
}
html_static_path = ["_static"]
html_css_files = ["custom.css"]
exclude_patterns = []
