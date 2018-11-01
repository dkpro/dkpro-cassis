from pathlib import Path

import pytest

from tests.fixtures import *
from tests.util import assert_xml_equal

from cassis import load_typesystem, TypeSystem


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


# Deserializing


@pytest.mark.parametrize(
    "typesystem_path",
    [
        pytest.lazy_fixture("small_typesystem_path"),
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
        pytest.lazy_fixture("dkpro_typesystem_xml"),
    ],
)
def test_deserializing_from_string(typesystem_xml):
    load_typesystem(typesystem_xml)


def test_deserializing_small_typesystem(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    assert len(list(typesystem.get_types())) == 3

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


@pytest.mark.parametrize(
    "typesystem_xml",
    [
        pytest.lazy_fixture("small_typesystem_xml"),
        pytest.lazy_fixture("typesystem_with_inheritance_xml"),
        pytest.lazy_fixture("dkpro_typesystem_xml"),
    ],
)
def test_serializing_typesystem_to_string(typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)

    actual_xml = typesystem.to_xml()

    assert_xml_equal(actual_xml, typesystem_xml)


@pytest.mark.parametrize(
    "typesystem_xml",
    [
        pytest.lazy_fixture("small_typesystem_xml"),
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
