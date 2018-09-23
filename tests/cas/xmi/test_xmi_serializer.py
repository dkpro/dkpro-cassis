from lxml_asserts import assert_xml_equal

from tests.fixtures import small_xmi, small_typesystem

from cassis.cas.xmi import *
import cassis.typesystem


def test_serializing_small_cas_to_string(small_xmi, small_typesystem):
    typesystem = cassis.typesystem.load_from_file(small_typesystem)
    cas = load_from_file(small_xmi, typesystem=typesystem)

    actual_xml = save_to_string(cas)

    with open(small_xmi, 'rb') as f:
        assert_xml_equal(actual_xml, f.read())


def test_serializing_small_cas_to_file(tmpdir, small_xmi, small_typesystem):
    typesystem = cassis.typesystem.load_from_file(small_typesystem)
    cas = load_from_file(small_xmi, typesystem=typesystem)
    path = tmpdir.join('cas.xml')

    save_to_file(cas, path)

    with open(path, 'rb') as actual, open(small_xmi, 'rb') as expected:
        assert_xml_equal(actual.read(), expected.read())
