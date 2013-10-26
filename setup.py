# -*- encoding: utf8 -*-
from setuptools import setup, find_packages

import os

setup(
    name = "python-redis-lock",
    version = "0.1.1",
    url = 'https://github.com/ionelmc/python-redis-lock',
    download_url = '',
    license = 'BSD',
    description = "Lock context manager implemented via redis SETNX/BLPOP.",
    long_description = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    author = 'Ionel Cristian Mărieș',
    author_email = 'contact@ionelmc.ro',
    packages = find_packages('src'),
    package_dir = {'':'src'},
    include_package_data = True,
    zip_safe = False,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Utilities',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    install_requires=[
        'redis>=2.8.0',
    ],
    extras_require={
        'django': [
            'django-redis>=3.3',
        ]
    }
)
