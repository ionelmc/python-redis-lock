extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]
source_suffix = '.rst'
master_doc = 'index'
project = 'redis-lock'
year = '2013-2026'
author = 'Ionel Cristian Mărieș'
copyright = f'{year}, {author}'
version = release = '4.0.0'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/ionelmc/python-redis-lock/issues/%s', '#%s'),
    'pr': ('https://github.com/ionelmc/python-redis-lock/pull/%s', 'PR #%s'),
}

html_theme = 'sphinx_py3doc_enhanced_theme'
html_theme_options = {
    'source_repository': 'https://github.com/ionelmc/python-redis-lock/',
    'source_branch': 'master',
    'source_directory': 'docs/',
    'footer_icons': [
        {
            'url': 'https://github.com/ionelmc/python-redis-lock/',
            'html': 'github.com/ionelmc/python-redis-lock',
        },
    ],
}

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_short_title = f'{project}-{version}'

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False
