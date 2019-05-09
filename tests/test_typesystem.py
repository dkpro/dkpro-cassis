from pathlib import Path
import warnings

import pytest

from tests.fixtures import *
from tests.util import assert_xml_equal

from cassis import load_typesystem, TypeSystem

TYPESYSTEM_FIXTURES = [
    pytest.lazy_fixture("small_typesystem_xml"),
    pytest.lazy_fixture("typesystem_with_inheritance_xml"),
    pytest.lazy_fixture("small_typesystem_with_predefined_types_xml"),
    pytest.lazy_fixture("dkpro_typesystem_xml"),
    pytest.lazy_fixture("typesystem_has_types_with_no_namespace_xml"),
]

# Feature


def test_feature_can_be_added():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    typesystem.add_feature(type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature")

    actual_type = typesystem.get_type("test.Type")
    actual_feature = actual_type.get_feature("testFeature")
    assert actual_feature.name == "testFeature"
    assert actual_feature.rangeTypeName == "String"
    assert actual_feature.description == "A test feature"


def test_feature_adding_throws_if_already_existing():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    typesystem.add_feature(type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature")

    with pytest.raises(ValueError):
        typesystem.add_feature(
            type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature"
        )


# Type


def test_type_can_be_created():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")

    assert test_type.name == "test.Type"
    assert test_type.supertypeName == "uima.tcas.Annotation"


def test_type_can_create_instances():
    typesystem = TypeSystem()
    test_type = typesystem.create_type(name="test.Type")
    typesystem.add_feature(type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature")

    annotation = test_type(begin=0, end=42, testFeature="testValue")

    assert annotation.begin == 0
    assert annotation.end == 42
    assert annotation.testFeature == "testValue"


def test_type_can_create_instance_with_inherited_fields():
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name="test.ParentType")
    typesystem.add_feature(type_=parent_type, name="parentFeature", rangeTypeName="String")

    child_type = typesystem.create_type(name="test.ChildType", supertypeName=parent_type.name)
    typesystem.add_feature(type_=child_type, name="childFeature", rangeTypeName="Integer")

    annotation = child_type(parentFeature="parent", childFeature="child")

    assert annotation.parentFeature == "parent"
    assert annotation.childFeature == "child"


def test_type_inherits_from_annotation_base():
    typesystem = TypeSystem()
    test_type = typesystem.create_type(name="test.Type", supertypeName="uima.cas.AnnotationBase")

    annotation = test_type(sofa=42)

    assert annotation.sofa == 42


def test_type_inherits_from_annotation():
    typesystem = TypeSystem()
    test_type = typesystem.create_type(name="test.Type")

    annotation = test_type(begin=0, end=42, sofa=1337)

    assert annotation.begin == 0
    assert annotation.end == 42
    assert annotation.sofa == 1337


@pytest.mark.parametrize(
    "type_name, expected",
    [
        ("uima.cas.Boolean", True),
        ("uima.cas.Byte", True),
        ("uima.cas.Short", True),
        ("uima.cas.Integer", True),
        ("uima.cas.Long", True),
        ("uima.cas.Float", True),
        ("uima.cas.Double", True),
        ("uima.cas.String", True),
        ("uima.cas.NonEmptyFloatList", False),
        ("uima.cas.IntegerList", False),
        ("uima.cas.EmptyIntegerList", False),
        ("uima.cas.NonEmptyIntegerList", False),
        ("uima.cas.StringList", False),
        ("uima.cas.EmptyStringList", False),
        ("uima.cas.NonEmptyStringList", False),
    ],
)
def test_is_primitive(type_name: str, expected: bool):
    typesystem = TypeSystem()

    assert typesystem.is_primitive(type_name) == expected


@pytest.mark.parametrize(
    "type_name, expected",
    [
        ("uima.cas.Boolean", False),
        ("uima.cas.Byte", False),
        ("uima.cas.Short", False),
        ("uima.cas.Integer", False),
        ("uima.cas.Long", False),
        ("uima.cas.Float", False),
        ("uima.cas.Double", False),
        ("uima.cas.String", False),
        ("uima.cas.NonEmptyFloatList", True),
        ("uima.cas.IntegerList", True),
        ("uima.cas.EmptyIntegerList", True),
        ("uima.cas.NonEmptyIntegerList", True),
        ("uima.cas.StringList", True),
        ("uima.cas.EmptyStringList", True),
        ("uima.cas.NonEmptyStringList", True),
    ],
)
def test_is_collection(type_name: str, expected: bool):
    typesystem = TypeSystem()

    assert typesystem.is_collection(type_name) == expected


@pytest.mark.parametrize(
    "type_name, expected",
    [
        ("uima.cas.ArrayBase", False),
        ("uima.cas.FSArray", False),
        ("uima.cas.FloatArray", True),
        ("uima.cas.IntegerArray", True),
        ("uima.cas.StringArray", True),
        ("uima.cas.ListBase", False),
        ("uima.cas.FSList", False),
        ("uima.cas.EmptyFSList", False),
        ("uima.cas.NonEmptyFSList", False),
        ("uima.cas.FloatList", True),
        ("uima.cas.EmptyFloatList", True),
        ("uima.cas.NonEmptyFloatList", True),
        ("uima.cas.IntegerList", True),
        ("uima.cas.EmptyIntegerList", True),
        ("uima.cas.NonEmptyIntegerList", True),
        ("uima.cas.StringList", True),
        ("uima.cas.EmptyStringList", True),
        ("uima.cas.NonEmptyStringList", True),
        ("uima.cas.BooleanArray", True),
        ("uima.cas.ByteArray", True),
        ("uima.cas.ShortArray", True),
        ("uima.cas.LongArray", True),
        ("uima.cas.DoubleArray", True),
    ],
)
def test_is_primitive_collection(type_name: str, expected: bool):
    typesystem = TypeSystem()

    assert typesystem.is_primitive_collection(type_name) == expected


# Deserializing


@pytest.mark.parametrize(
    "typesystem_path",
    [
        pytest.lazy_fixture("small_typesystem_path"),
        pytest.lazy_fixture("small_typesystem_with_predefined_types_path"),
        pytest.lazy_fixture("typesystem_with_inheritance_path"),
        pytest.lazy_fixture("dkpro_typesystem_path"),
    ],
)
def test_deserializing_from_file(typesystem_path):
    with open(typesystem_path, "rb") as f:
        load_typesystem(f)


@pytest.mark.parametrize(
    "typesystem_xml",
    [
        pytest.lazy_fixture("small_typesystem_xml"),
        pytest.lazy_fixture("typesystem_with_inheritance_xml"),
        pytest.lazy_fixture("small_typesystem_with_predefined_types_xml"),
        pytest.lazy_fixture("dkpro_typesystem_xml"),
    ],
)
def test_deserializing_from_string(typesystem_xml):
    load_typesystem(typesystem_xml)


def test_deserializing_small_typesystem(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    assert len(list(typesystem.get_types())) == 2

    # Assert annotation type
    annotation_type = typesystem.get_type("uima.tcas.DocumentAnnotation")
    assert annotation_type.name == "uima.tcas.DocumentAnnotation"
    assert annotation_type.supertypeName == "uima.tcas.Annotation"

    language_feature = annotation_type.get_feature("language")
    assert language_feature.name == "language"
    assert language_feature.rangeTypeName == "uima.cas.String"

    # Assert token type
    token_type = typesystem.get_type("cassis.Token")
    assert token_type.name == "cassis.Token"
    assert token_type.supertypeName == "uima.tcas.Annotation"

    token_id_feature = token_type.get_feature("id")
    assert token_id_feature.name == "id"
    assert token_id_feature.rangeTypeName == "uima.cas.Integer"

    token_pos_feature = token_type.get_feature("pos")
    assert token_pos_feature.name == "pos"
    assert token_pos_feature.rangeTypeName == "uima.cas.String"

    # Assert sentence type
    sentence_type = typesystem.get_type("cassis.Sentence")
    assert sentence_type.name == "cassis.Sentence"
    assert sentence_type.supertypeName == "uima.tcas.Annotation"

    sentence_type_id_feature = sentence_type.get_feature("id")
    assert sentence_type_id_feature.name == "id"
    assert sentence_type_id_feature.rangeTypeName == "uima.cas.Integer"


# Serializing


@pytest.mark.parametrize("typesystem_xml", TYPESYSTEM_FIXTURES)
def test_serializing_typesystem_to_string(typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)

    actual_xml = typesystem.to_xml()

    assert_xml_equal(actual_xml, typesystem_xml)


@pytest.mark.parametrize(
    "typesystem_xml",
    [
        pytest.lazy_fixture("small_typesystem_xml"),
        pytest.lazy_fixture("small_typesystem_with_predefined_types_xml"),
        pytest.lazy_fixture("typesystem_with_inheritance_xml"),
        pytest.lazy_fixture("dkpro_typesystem_xml"),
    ],
)
def test_serializing_typesystem_to_file_path(tmpdir, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    path = Path(str(tmpdir.join("typesystem.xml")))

    typesystem.to_xml(path)

    with path.open("rb") as actual:
        assert_xml_equal(actual, typesystem_xml)


@pytest.mark.parametrize(
    "typesystem_xml",
    [
        pytest.lazy_fixture("small_typesystem_xml"),
        pytest.lazy_fixture("small_typesystem_with_predefined_types_xml"),
        pytest.lazy_fixture("typesystem_with_inheritance_xml"),
        pytest.lazy_fixture("dkpro_typesystem_xml"),
    ],
)
def test_serializing_typesystem_to_file(tmpdir, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    path = str(tmpdir.join("typesystem.xml"))

    typesystem.to_xml(path)

    with open(path, "rb") as actual:
        assert_xml_equal(actual, typesystem_xml)


# Type system with inheritance and redefined features
# https://github.com/dkpro/dkpro-cassis/issues/56


def test_that_typesystem_with_child_redefining_type_same_warns():
    path = os.path.join(FIXTURE_DIR, "typesystems", "typesystem_with_inheritance_redefined_same.xml")
    with pytest.warns(UserWarning):
        with open(path, "rb") as f:
            load_typesystem(f)


def test_that_typesystem_with_child_redefining_type_differently_throws():
    path = os.path.join(FIXTURE_DIR, "typesystems", "typesystem_with_inheritance_redefined_different.xml")
    with pytest.raises(ValueError):
        with open(path, "rb") as f:
            load_typesystem(f)
