import os

import pytest

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'test_files'
)


@pytest.fixture
def small_xmi():
    return os.path.join(FIXTURE_DIR, 'xmi', 'small_cas.xmi')


@pytest.fixture
def small_typesystem():
    return os.path.join(FIXTURE_DIR, 'typesystems', 'small_typesystem.xml')
