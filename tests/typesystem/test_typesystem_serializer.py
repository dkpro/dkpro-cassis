import lxml.etree as etree

from lxml_asserts import assert_xml_equal

from tests.fixtures import small_typesystem

from cassis.typesystem import *


def test_serializing_small_typesystem_to_string(small_typesystem):
    typesystem = load_from_file(small_typesystem)

    actual_xml = save_to_string(typesystem)

    with open(small_typesystem, 'rb') as f:
        assert_xml_equal(actual_xml, f.read())


def test_serializing_small_typesystem_to_file(tmpdir, small_typesystem):
    typesystem = load_from_file(small_typesystem)
    path = tmpdir.join('typesystem.xml')

    save_to_file(typesystem, path)

    with open(path, 'rb') as actual, open(small_typesystem, 'rb') as expected:
        assert_xml_equal(actual.read(), expected.read())
