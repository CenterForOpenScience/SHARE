#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import alabaster
extensions = [
    'sphinx.ext.todo',
]
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'SHARE'
copyright = '2016, Center for Open Science'
author = 'Center for Open Science'
version = release = '2.0'

exclude_patterns = ['_build']

# THEME
html_theme = 'alabaster'
html_theme_path = [alabaster.get_path()]
html_theme = 'alabaster'
html_static_path = ['_static']
templates_path = ['_templates']
html_show_sourcelink = False
html_theme_options = {
    'logo': 'share.png',
    'description': 'A free, open, dataset about research and scholarly activities across the lifecycle.',
    'description_font_style': 'italic',
    'github_user': 'CenterForOpenScience',
    'github_repo': 'SHARE',
    'github_banner': True,
    'github_button': False,
}
html_sidebars = {
    'index': [
        'about.html',
        'localtoc.html',
        'searchbox.html'
    ],
    '**': [
        'about.html',
        'localtoc.html',
        'relations.html',
        'searchbox.html',
    ]
}
