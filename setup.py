# !/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the "upload" functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import setup, Command, find_packages

# Package meta-data.
NAME = "dkpro-cassis"
DESCRIPTION = "UIMA CAS processing library in Python"
HOMEPAGE = "https://dkpro.github.io"
EMAIL = "dkpro-core-user@googlegroups.com"
AUTHOR = "The DKPro cassis team"
REQUIRES_PYTHON = ">=3.7.0"

install_requires = [
    "lxml~=4.9.1",
    "attrs==21.2.*",
    "sortedcontainers==2.4.*",
    "toposort==1.7",
    "more-itertools==8.12.*",
    "deprecation==2.1.*",
    "importlib_resources==5.4.*"
]

test_dependencies = [
    "tox==3.24.*",
    "pytest==6.2.*",
    "lxml-asserts==0.1.*",
    "pytest-lazy-fixture==0.6.*",
    "codecov==2.1.*",
    "pytest-cov==3.0.*",
    "rstcheck==3.3.*"
]

dev_dependencies = [
    "black==21.12b0",
    "isort==5.10.*"
]

doc_dependencies = [
    "sphinx",
    "sphinx-autodoc-typehints",
    "sphinx-rtd-theme"
]

extras = {
    "test": test_dependencies,
    "dev":  dev_dependencies,
    "doc":  doc_dependencies
}

# The rest you shouldn"t have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if "README.rst" is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package"s __version__.py module as a dictionary.
about = {}
with open(os.path.join(here, "cassis", "__version__.py")) as f:
    exec(f.read(), about)


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=HOMEPAGE,
    keywords="uima dkpro cas xmi",

    project_urls={
        "Bug Tracker": "https://github.com/dkpro/dkpro-cassis/issues",
        "Documentation": "https://cassis.readthedocs.org/",
        "Source Code": "https://github.com/dkpro/dkpro-cassis",
    },

    packages=find_packages(exclude="tests"),
    package_data={"cassis": ["resources/*.xml"]},

    install_requires=install_requires,
    test_suite="tests",

    tests_require=test_dependencies,
    extras_require=extras,

    include_package_data=True,
    license="Apache License 2.0",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Text Processing :: Linguistic"
    ],
)
