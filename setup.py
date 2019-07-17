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
REQUIRES_PYTHON = ">=3.5.0"

install_requires=[
    "lxml",
    "attrs",
    "sortedcontainers",
    "toposort",
    "more-itertools"
]

test_dependencies = [
    "tox",
    "pytest",
    "lxml-asserts",
    "pytest-lazy-fixture",
    "codecov",
    "pytest-cov",
]

dev_dependencies = [
    "black",
    "twine"
]

doc_dependencies = [
    "sphinx",
    "sphinx-autodoc-typehints",
    "sphinx-rtd-theme"
]

extras = {
    "test" : test_dependencies,
    "dev": dev_dependencies,
    "doc": doc_dependencies
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


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        sys.exit()


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
    packages=find_packages(exclude="tests"),
    keywords="uima dkpro cas xmi",

    project_urls={
        "Bug Tracker": "https://github.com/dkpro/dkpro-cassis/issues",
        "Documentation": "https://cassis.readthedocs.org/",
        "Source Code": "https://github.com/dkpro/dkpro-cassis",
    },

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
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Text Processing :: Linguistic"
    ],

    # $ setup.py publish support.
    cmdclass={
        "upload": UploadCommand,
    },
)
