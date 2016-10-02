#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import alabaster

from jester import __version__, version_info


project = 'jester'
copyright = '2016, Dave Shawley'
version = __version__
release = '.'.join(str(x) for x in version_info[:2])

needs_sphinx = '1.0'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]
templates_path = []
source_suffix = '.rst'
source_encoding = 'utf-8-sig'
master_doc = 'index'
pygments_style = 'sphinx'
html_theme = 'alabaster'
html_theme_path = [alabaster.get_path()]
html_theme_options = {
    'github_user': 'dave-shawley',
    'github_repo': 'jester',
    'github_banner': True,
    'description': 'Async HTTP Engine',
    'fixed_sidebar': True,
}
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
    ]
}
html_static_path = []
exclude_patterns = []

intersphinx_mapping = {
    'python': ('http://docs.python.org/', None),
}
