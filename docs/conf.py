# Sphinx configuration — Home Care Cost Model

project = "Home Care Cost Model"
copyright = "2026, Dave Cook"
author = "Dave Cook"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]

html_theme_options = {
    "description": "A reference cost model for Canadian home care service-mix decisions.",
    "github_user": "DaveCookVectorLabs",
    "github_repo": "home-care-cost-model",
}
