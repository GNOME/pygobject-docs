# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


project = "GNOME Python API"
author = "GNOME Developers"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.intersphinx",
]

# include_patterns = ["build/source/**"]
templates_path: list[str] = ["./sphinx"]
exclude_patterns: list[str] = []

# Default role for backtick text `like this`.
# default_role = "py:obj"
add_module_names = False
# toc_object_entries = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = "alabaster"

# See https://alabaster.readthedocs.io/en/latest/customization.html
html_theme_options = {
    "globaltoc_maxdepth": 2,
    "fixed_sidebar": False,
}

# html_static_path = ["_static"]
html_sidebars = {
    "**": ["about.html", "searchbox.html", "globaltoc.html"],
}

# -- Intersphinx

intersphinx_mapping = {"https://docs.python.org/": None}
