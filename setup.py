#!/usr/bin/env python
# http://docs.python.org/distutils/setupscript.html
# http://docs.python.org/2/distutils/examples.html

from setuptools import setup
import re
import os


name = 'dsnparse'
with open("{}.py".format(name), 'rU') as f:
    version = re.search("^__version__\s*=\s*[\'\"]([^\'\"]+)", f.read(), flags=re.I | re.M).group(1)

setup(
    name=name,
    version=version,
    description='parse dsn urls',
    author='Jay Marcyes',
    author_email='jay@marcyes.com',
    url='http://github.com/Jaymon/{}'.format(name),
    py_modules=[name],
    license="MIT",
    classifiers=[ # https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite = "dsnparse_test",
)
