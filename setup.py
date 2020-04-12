#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
KISS protocol in Python, setup.

Source:: https://github.com/henkvanasselt/pykiss
"""

import os
import setuptools
import sys

__title__ = 'pykiss'
__version__ = '0.0.7'
__author__ = 'Henk van Asselt'  # 
__copyright__ = 'Copyright 2020 Henk van Asselt'
__license__ = 'Apache License, Version 2.0'


# def publish():
    # """Function for publishing package to pypi."""
    # if sys.argv[-1] == 'publish':
        # os.system('python setup.py sdist')
        # os.system('twine upload dist/*')
        # sys.exit()


# publish()


setuptools.setup(
    name=__title__,
    version=__version__,
    description='Python KISS.',
    author='Henk van Asselt',
    author_email='',
    packages=['kiss'],
    package_data={'': ['LICENSE']},
    package_dir={'pykiss': 'pykiss'},
    license=open('LICENSE').read(),
    long_description=open('README.rst').read(),
    url='https://github.com/henkvanasselt/pykiss',
    zip_safe=False,
    setup_requires=['pyserial',
    ],
    install_requires=['pyserial >= 3.4'],
    classifiers=[
        'Topic :: Communications :: Ham Radio',
        'Programming Language :: Python',
        'License :: OSI Approved :: Apache Software License'
    ],
    keywords=[
        'Ham Radio', 'APRS', 'KISS'
    ]
)
