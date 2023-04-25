# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


project = "GNOME Python API"
author = "GNOME Developers"
copyright = "2023"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.intersphinx",
]

# include_patterns = ["build/source/**"]
templates_path: list[str] = ["./sphinx"]
exclude_patterns: list[str] = []

# Default role for backtick text `like this`.
default_role = "py:obj"
add_module_names = False
# toc_object_entries = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = "alabaster"
pygments_style = "tango"
html_theme = "sphinx_rtd_theme"
html_show_copyright = False
html_title = project

html_theme_options = {
    "display_version": False,
    "globaltoc_maxdepth": 2,
    "prev_next_buttons_location": None,
}

html_static_path = ["static"]

html_css_files = ["custom.css"]

# -- Intersphinx

intersphinx_mapping = {"https://docs.python.org/": None}
