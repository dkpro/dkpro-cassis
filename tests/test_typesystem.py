import warnings
from pathlib import Path

import pytest as pytest

from cassis.typesystem import (
    _COLLECTION_TYPES,
    TOP_TYPE_NAME,
    TYPE_NAME_ANNOTATION,
    TYPE_NAME_ANNOTATION_BASE,
    TYPE_NAME_ARRAY_BASE,
    TYPE_NAME_BOOLEAN,
    TYPE_NAME_INTEGER,
    TYPE_NAME_SOFA,
    TYPE_NAME_STRING,
    TYPE_NAME_STRING_ARRAY,
    TYPE_NAME_TOP,
    TypeCheckError,
    is_predefined,
)
from tests.fixtures import *
from tests.util import assert_xml_equal

TYPESYSTEM_FIXTURES = [
    pytest.lazy_fixture("small_typesystem_xml"),
    pytest.lazy_fixture("typesystem_with_inheritance_xml"),
    pytest.lazy_fixture("small_typesystem_with_predefined_types_xml"),
    pytest.lazy_fixture("dkpro_typesystem_xml"),
    pytest.lazy_fixture("typesystem_has_types_with_no_namespace_xml"),
    pytest.lazy_fixture("typesystem_with_redefined_documentannotation_xml"),
    pytest.lazy_fixture("typesystem_with_reserved_names_xml"),
    pytest.lazy_fixture("webanno_typesystem_xml"),
    pytest.lazy_fixture("inception_typesystem_xml"),
]

# Feature


def test_feature_can_be_created():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    typesystem.create_feature(
        domainType=test_type, name="testFeature", rangeType=TYPE_NAME_STRING, description="A test feature"
    )

    actual_type = typesystem.get_type("test.Type")
    assert actual_type.typesystem == typesystem

    actual_feature = actual_type.get_feature("testFeature")
    assert actual_feature.name == "testFeature"
    assert actual_feature.domainType.name == test_type.name
    assert actual_feature.rangeType.name == TYPE_NAME_STRING
    assert actual_feature.description == "A test feature"


def test_feature_creation_warns_if_redefined_identically():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")

    feature1 = typesystem.create_feature(
        domainType=test_type, name="testFeature", rangeType=TYPE_NAME_STRING, description="A test feature"
    )

    with pytest.warns(UserWarning):
        feature2 = typesystem.create_feature(
            domainType=test_type, name="testFeature", rangeType=TYPE_NAME_STRING, description="A test feature"
        )

    assert feature1.domainType.name == test_type.name
    assert feature2.domainType.name == test_type.name


def test_feature_domain_when_feature_redefined_in_child():
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name="test.Parent")
    child_type = typesystem.create_type(name="test.Child", supertypeName="test.Parent")

    feature_parent = typesystem.create_feature(domainType=parent_type, name="testFeature", rangeType=TYPE_NAME_STRING)

    assert feature_parent.domainType.name == parent_type.name

    with pytest.warns(UserWarning):
        # UserWarning: Feature with name [testFeature] already exists in parent!
        feature_child = typesystem.create_feature(domainType=child_type, name="testFeature", rangeType=TYPE_NAME_STRING)

    assert feature_parent.domainType.name == parent_type.name
    assert feature_child.domainType.name == child_type.name


def test_feature_domain_when_feature_added_to_parent_retroactively():
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name="test.Parent")
    child_type = typesystem.create_type(name="test.Child", supertypeName="test.Parent")

    feature_child = typesystem.create_feature(domainType=child_type, name="testFeature", rangeType=TYPE_NAME_STRING)

    assert feature_child.domainType.name == child_type.name

    feature_parent = typesystem.create_feature(domainType=parent_type, name="testFeature", rangeType=TYPE_NAME_STRING)

    assert feature_parent.domainType.name == parent_type.name
    assert feature_child.domainType.name == child_type.name


def test_feature_adding_throws_if_redefined_differently():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    typesystem.create_feature(
        domainType=test_type, name="testFeature", rangeType=TYPE_NAME_STRING, description="A test feature"
    )

    with pytest.raises(ValueError):
        typesystem.create_feature(
            domainType=test_type, name="testFeature", rangeType=TYPE_NAME_BOOLEAN, description="A test feature"
        )


def test_get_feature_own():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    feature = typesystem.create_feature(domainType=test_type, name="testFeature", rangeType=TYPE_NAME_STRING)

    assert test_type.get_feature("testFeature") == feature


def test_get_feature_inherited():
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name="test.ParentType")
    parent_feature = typesystem.create_feature(domainType=parent_type, name="parentFeature", rangeType=TYPE_NAME_STRING)

    child_type = typesystem.create_type(name="test.ChildType", supertypeName=parent_type.name)

    assert parent_type.get_feature("parentFeature") == parent_feature
    assert child_type.get_feature("parentFeature") == parent_feature


def test_type_can_get_all_features():
    typesystem = TypeSystem()
    test_type = typesystem.create_type(name="test.Type")

    expected_features = [test_type.get_feature("begin"), test_type.get_feature("end"), test_type.get_feature("sofa")]

    for feature_name in ["a", "b", "c", "d"]:
        feature = typesystem.create_feature(test_type, f"test_feature_{feature_name}", rangeType=TYPE_NAME_STRING)
        expected_features.append(feature)

    actual_all_features = test_type.all_features

    actual_all_features.sort()
    expected_features.sort()

    assert actual_all_features == expected_features


def test_type_can_get_all_features_with_in_between_added_features():
    typesystem = TypeSystem()
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name="test.ParentType", supertypeName=TYPE_NAME_TOP)

    child_type = typesystem.create_type(name="test.ChildType", supertypeName=parent_type.name)
    child_feature = typesystem.create_feature(domainType=child_type, name="childFeature", rangeType=TYPE_NAME_INTEGER)

    assert child_type.all_features == [child_feature]

    parent_feature = typesystem.create_feature(domainType=parent_type, name="parentFeature", rangeType=TYPE_NAME_STRING)

    assert child_type.all_features == [child_feature, parent_feature]


# Type


def test_type_can_be_created():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")

    assert test_type.name == "test.Type"
    assert test_type.supertype.name == "uima.tcas.Annotation"


def test_type_can_create_instances():
    typesystem = TypeSystem()
    test_type = typesystem.create_type(name="test.Type")
    typesystem.create_feature(
        domainType=test_type, name="testFeature", rangeType=TYPE_NAME_STRING, description="A test feature"
    )

    annotation = test_type(begin=0, end=42, testFeature="testValue")

    assert annotation.begin == 0
    assert annotation.end == 42
    assert annotation.testFeature == "testValue"


def test_type_can_create_instance_with_inherited_fields():
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name="test.ParentType")
    typesystem.create_feature(domainType=parent_type, name="parentFeature", rangeType=TYPE_NAME_STRING)

    child_type = typesystem.create_type(name="test.ChildType", supertypeName=parent_type.name)
    typesystem.create_feature(domainType=child_type, name="childFeature", rangeType=TYPE_NAME_INTEGER)

    annotation = child_type(parentFeature="parent", childFeature="child")

    assert annotation.parentFeature == "parent"
    assert annotation.childFeature == "child"


def test_type_can_create_instance_with_deeply_inherited_fields(typesystem_with_inheritance_xml):
    # https://github.com/dkpro/dkpro-cassis/issues/97
    typesystem = load_typesystem(typesystem_with_inheritance_xml)

    t = typesystem.get_type("cassis.GrandGrandGrandChild")

    assert "parentFeature" in t._inherited_features
    assert "childFeature" in t._inherited_features


def test_type_can_retrieve_children(typesystem_with_inheritance_xml):
    typesystem = load_typesystem(typesystem_with_inheritance_xml)

    t = typesystem.get_type("cassis.Child")

    children = [item.name for item in t.children]

    assert children == ["cassis.GrandChild"]


def test_type_can_retrieve_descendants(typesystem_with_inheritance_xml):
    typesystem = load_typesystem(typesystem_with_inheritance_xml)

    t = typesystem.get_type("cassis.Child")

    descendants = [item.name for item in t.descendants]

    assert descendants == ["cassis.Child", "cassis.GrandChild", "cassis.GrandGrandChild", "cassis.GrandGrandGrandChild"]


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


# Type checking


@pytest.mark.parametrize(
    "type_name, expected",
    [
        ("uima.cas.TOP", True),
        ("uima.cas.NULL", True),
        ("uima.cas.Boolean", True),
        ("uima.cas.Byte", True),
        ("uima.cas.Short", True),
        ("uima.cas.Integer", True),
        ("uima.cas.Long", True),
        ("uima.cas.Float", True),
        ("uima.cas.Double", True),
        ("uima.cas.String", True),
        ("uima.cas.ArrayBase", True),
        ("uima.cas.FSArray", True),
        ("uima.cas.FloatArray", True),
        ("uima.cas.IntegerArray", True),
        ("uima.cas.StringArray", True),
        ("uima.cas.ListBase", True),
        ("uima.cas.FSList", True),
        ("uima.cas.EmptyFSList", True),
        ("uima.cas.NonEmptyFSList", True),
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
        ("uima.cas.Sofa", True),
        ("uima.cas.AnnotationBase", True),
        ("uima.tcas.Annotation", True),
        ("example.TypeA", False),
        ("example.TypeB", False),
        ("example.TypeC", False),
    ],
)
def test_is_predefined(type_name: str, expected: bool):

    assert is_predefined(type_name) == expected


@pytest.mark.parametrize(
    "child_name, parent_name, expected",
    [
        (
            "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph",
            "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Div",
            True,
        ),
        ("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemArgLink", "uima.cas.String", False),
        ("de.tudarmstadt.ukp.dkpro.core.api.syntax.type.chunk.VC", "uima.tcas.Annotation", True),
        ("de.tudarmstadt.ukp.dkpro.core.api.transform.type.SofaChangeAnnotation", "uima.tcas.Annotation", True),
        (
            "de.tudarmstadt.ukp.dkpro.core.api.anomaly.type.SpellingAnomaly",
            "de.tudarmstadt.ukp.dkpro.core.api.anomaly.type.GrammarAnomaly",
            False,
        ),
        ("de.tudarmstadt.ukp.dkpro.core.api.ner.type.Quantity", TOP_TYPE_NAME, True),
    ],
)
def test_is_instance_of(child_name: str, parent_name: str, expected: bool):
    # We cannot use fixtures and parameterize at the same time, so we
    # manually load the type system
    path = os.path.join(FIXTURE_DIR, "typesystems", "important_dkpro_types.xml")

    with open(path) as f:
        ts = load_typesystem(f.read())

    assert ts.is_instance_of(child_name, parent_name) == expected


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

    assert typesystem.is_primitive(type_name) is expected


def test_is_primitive_when_parent_is_primitive():
    typesystem = TypeSystem()
    typesystem.create_type("test.string", "uima.cas.String")

    assert typesystem.is_primitive("test.string")


@pytest.mark.parametrize(
    "type_name, feature_name, expected",
    [
        ("uima.cas.TOP", "uima.cas.Boolean", False),
        ("uima.cas.TOP", "uima.cas.Byte", False),
        ("uima.cas.TOP", "uima.cas.Short", False),
        ("uima.cas.TOP", "uima.cas.Integer", False),
        ("uima.cas.TOP", "uima.cas.Long", False),
        ("uima.cas.TOP", "uima.cas.Float", False),
        ("uima.cas.TOP", "uima.cas.Double", False),
        ("uima.cas.TOP", "uima.cas.String", False),
        ("uima.cas.TOP", "uima.cas.NonEmptyFloatList", True),
        ("uima.cas.TOP", "uima.cas.IntegerList", True),
        ("uima.cas.TOP", "uima.cas.EmptyIntegerList", True),
        ("uima.cas.TOP", "uima.cas.NonEmptyIntegerList", True),
        ("uima.cas.TOP", "uima.cas.StringList", True),
        ("uima.cas.TOP", "uima.cas.EmptyStringList", True),
        ("uima.cas.TOP", "uima.cas.NonEmptyStringList", True),
        ("uima.cas.TOP", "uima.cas.NonEmptyFloatList", True),
        ("uima.cas.TOP", "uima.cas.IntegerList", True),
        ("uima.cas.TOP", "uima.cas.EmptyIntegerList", True),
        ("uima.cas.TOP", "uima.cas.NonEmptyIntegerList", True),
        ("uima.cas.TOP", "uima.cas.StringList", True),
        ("uima.cas.TOP", "uima.cas.EmptyStringList", True),
        ("uima.cas.TOP", "uima.cas.NonEmptyStringList", True),
        ("uima.cas.NonEmptyFloatList", "uima.cas.Boolean", False),
        ("uima.cas.IntegerList", "uima.cas.Byte", False),
        ("uima.cas.EmptyIntegerList", "uima.cas.Short", False),
        ("uima.cas.NonEmptyIntegerList", "uima.cas.Integer", False),
        ("uima.cas.StringList", "uima.cas.Long", False),
        ("uima.cas.EmptyStringList", "uima.cas.Float", False),
        ("uima.cas.NonEmptyStringList", "uima.cas.Double", False),
    ],
)
def test_is_collection(type_name: str, feature_name: str, expected: bool):
    typesystem = TypeSystem()
    t = typesystem.get_type(type_name)
    feature = typesystem.create_feature(t, "test_feature", rangeType=typesystem.get_type(feature_name))

    assert typesystem.is_collection(type_name, feature) == expected


@pytest.mark.filterwarnings("ignore:Feature with name")
@pytest.mark.parametrize("type_name", [c for c in _COLLECTION_TYPES])
def test_is_collection_for_builtin_collections_with_elements(type_name: str):
    typesystem = TypeSystem()
    t = typesystem.get_type(type_name)

    feature = typesystem.create_feature(t, "elements", rangeType=typesystem.get_type(TYPE_NAME_TOP))

    assert typesystem.is_collection(type_name, feature) is True


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


@pytest.mark.parametrize(
    "type_name, expected",
    [
        ("uima.cas.TOP", False),
        ("uima.cas.ArrayBase", False),
        ("uima.cas.FSArray", False),
        ("uima.cas.FloatArray", True),
        ("uima.cas.IntegerArray", True),
        ("uima.cas.StringArray", True),
        ("uima.cas.ListBase", False),
        ("uima.cas.FSList", False),
        ("uima.cas.EmptyFSList", False),
        ("uima.cas.NonEmptyFSList", False),
        ("uima.cas.FloatList", False),
        ("uima.cas.EmptyFloatList", False),
        ("uima.cas.NonEmptyFloatList", False),
        ("uima.cas.IntegerList", False),
        ("uima.cas.EmptyIntegerList", False),
        ("uima.cas.NonEmptyIntegerList", False),
        ("uima.cas.StringList", False),
        ("uima.cas.EmptyStringList", False),
        ("uima.cas.NonEmptyStringList", False),
        ("uima.cas.BooleanArray", True),
        ("uima.cas.ByteArray", True),
        ("uima.cas.ShortArray", True),
        ("uima.cas.LongArray", True),
        ("uima.cas.DoubleArray", True),
    ],
)
def test_is_primitive_collection(type_name: str, expected: bool):
    typesystem = TypeSystem()

    assert typesystem.is_primitive_array(type_name) == expected


def test_is_array():
    cas = Cas()

    for type in cas.typesystem.get_types():
        assert cas.typesystem.is_array(type.name) == type.name.endswith("Array")


@pytest.mark.parametrize(
    "parent_name, child_name, expected",
    [
        ("uima.cas.ArrayBase", "uima.cas.ShortArray", True),
        ("uima.cas.FSList", "uima.cas.ShortArray", False),
        ("uima.cas.ListBase", "uima.cas.NonEmptyFSList", True),
        ("uima.cas.FSList", "uima.cas.NonEmptyFSList", True),
        ("uima.cas.FloatList", "uima.cas.NonEmptyIntegerList", False),
        ("uima.cas.EmptyIntegerList", "uima.cas.IntegerList", False),
        ("uima.cas.Sofa", "uima.cas.Sofa", True),
        ("uima.cas.TOP", "uima.cas.Sofa", True),
        ("uima.cas.TOP", "uima.cas.TOP", True),
    ],
)
def test_subsumes_deprecated(parent_name: str, child_name: str, expected: bool):
    ts = TypeSystem()
    assert ts.subsumes(parent_name, child_name) == expected


@pytest.mark.parametrize(
    "parent_name, child_name, expected",
    [
        ("uima.cas.ArrayBase", "uima.cas.ShortArray", True),
        ("uima.cas.FSList", "uima.cas.ShortArray", False),
        ("uima.cas.ListBase", "uima.cas.NonEmptyFSList", True),
        ("uima.cas.FSList", "uima.cas.NonEmptyFSList", True),
        ("uima.cas.FloatList", "uima.cas.NonEmptyIntegerList", False),
        ("uima.cas.EmptyIntegerList", "uima.cas.IntegerList", False),
        ("uima.cas.Sofa", "uima.cas.Sofa", True),
        ("uima.cas.TOP", "uima.cas.Sofa", True),
        ("uima.cas.TOP", "uima.cas.TOP", True),
    ],
)
def test_subsumes(parent_name: str, child_name: str, expected: bool):
    ts = TypeSystem()
    parent_type = ts.get_type(parent_name)
    child_type = ts.get_type(child_name)
    assert parent_type.subsumes(child_type) == expected


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


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("typesystem_xml", TYPESYSTEM_FIXTURES)
def test_deserializing_from_string(typesystem_xml):
    load_typesystem(typesystem_xml)


def test_deserializing_small_typesystem(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    # There are two types in the type system and we implicitly
    # define DocumentAnnotation
    assert len(list(typesystem.get_types())) == 3

    # Assert annotation type
    annotation_type = typesystem.get_type("uima.tcas.DocumentAnnotation")
    assert annotation_type.name == "uima.tcas.DocumentAnnotation"
    assert annotation_type.supertype.name == "uima.tcas.Annotation"

    language_feature = annotation_type.get_feature("language")
    assert language_feature.name == "language"
    assert language_feature.rangeType.name == "uima.cas.String"

    # Assert token type
    token_type = typesystem.get_type("cassis.Token")
    assert token_type.name == "cassis.Token"
    assert token_type.supertype.name == "uima.tcas.Annotation"

    token_id_feature = token_type.get_feature("id")
    assert token_id_feature.name == "id"
    assert token_id_feature.rangeType.name == "uima.cas.Integer"

    token_pos_feature = token_type.get_feature("pos")
    assert token_pos_feature.name == "pos"
    assert token_pos_feature.rangeType.name == "uima.cas.String"
    assert token_pos_feature.multipleReferencesAllowed is True

    # Assert sentence type
    sentence_type = typesystem.get_type("cassis.Sentence")
    assert sentence_type.name == "cassis.Sentence"
    assert sentence_type.supertype.name == "uima.tcas.Annotation"

    sentence_type_id_feature = sentence_type.get_feature("id")
    assert sentence_type_id_feature.name == "id"
    assert sentence_type_id_feature.rangeType.name == "uima.cas.Integer"
    assert sentence_type_id_feature.multipleReferencesAllowed is False


# Serializing


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("typesystem_xml", TYPESYSTEM_FIXTURES)
def test_serializing_typesystem_to_string(typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)

    actual_xml = typesystem.to_xml()

    assert_xml_equal(actual_xml, typesystem_xml)


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("typesystem_xml", TYPESYSTEM_FIXTURES)
def test_serializing_typesystem_to_file_path(tmpdir, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    path = Path(str(tmpdir.join("typesystem.xml")))

    typesystem.to_xml(path)

    with path.open("rb") as actual:
        assert_xml_equal(actual, typesystem_xml)


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("typesystem_xml", TYPESYSTEM_FIXTURES)
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


# DocumentAnnotation support
# https://github.com/dkpro/dkpro-cassis/issues/56


def test_that_typesystem_with_redefined_documentation_annotation_works(
    typesystem_with_redefined_documentannotation_xml,
):
    typesystem = load_typesystem(typesystem_with_redefined_documentannotation_xml)

    actual_xml = typesystem.to_xml()

    assert_xml_equal(actual_xml, typesystem_with_redefined_documentannotation_xml)


# Merging of type systems
# We take some tests from https://github.com/apache/uima-uimaj/blob/master/uimaj-core/src/test/java/org/apache/uima/util/CasCreationUtilsTest.java


@pytest.mark.parametrize(
    "name, rangeTypeName, elementType, multipleReferencesAllowed",
    [
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.tcas.Annotation", True),  # Same multiref
        ("arrayNoMultiRefs", "uima.cas.FSArray", "uima.tcas.Annotation", None),  # Default multiref
        ("arrayNoMultiRefs", "uima.cas.FSArray", "uima.tcas.Annotation", None),  # Same elementType
        ("listMultiRefsOk", "uima.cas.FSList", "uima.tcas.Annotation", None),  # Default elementType
        ("arrayTop", "uima.cas.FSArray", None, None),  # No elementType,
    ],
)
def test_that_merging_compatible_typesystem_works(name, rangeTypeName, elementType, multipleReferencesAllowed):
    with open(typesystem_merge_base_path()) as f:
        base = load_typesystem(f.read())

    ts = TypeSystem()
    t = ts.create_type("test.ArraysAndListsWithElementTypes", supertypeName="uima.cas.TOP")
    ts.create_feature(
        domainType=t,
        name=name,
        rangeType=rangeTypeName,
        elementType=elementType,
        multipleReferencesAllowed=multipleReferencesAllowed,
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)

        result = merge_typesystems(base, ts)

    assert result.contains_type("test.ArraysAndListsWithElementTypes")


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize(
    "name, rangeTypeName, elementType, multipleReferencesAllowed",
    [
        ("arrayNoElementType", "uima.cas.FSArray", "uima.tcas.Annotation", None),  # Different elementTypes
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.cas.AnnotationBase", True),  # Different elementTypes
        ("arrayMultiRefsOk", "uima.cas.FSList", "uima.tcas.Annotation", True),  # Incompatible rangeTypes
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.cas.TOP", False),  # Different multiref
        ("arrayNoMultiRefs", "uima.cas.FSArray", "uima.cas.TOP", True),  # Different multiref
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.cas.TOP", None),  # Different multiref default
    ],
)
def test_that_merging_incompatible_typesystem_throws(name, rangeTypeName, elementType, multipleReferencesAllowed):
    with open(typesystem_merge_base_path()) as f:
        base = load_typesystem(f.read())

    ts = TypeSystem()
    t = ts.create_type("test.ArraysAndListsWithElementTypes", supertypeName="uima.cas.TOP")
    ts.create_feature(
        domainType=t,
        name=name,
        rangeType=rangeTypeName,
        elementType=elementType,
        multipleReferencesAllowed=multipleReferencesAllowed,
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with pytest.raises(ValueError, match=rf".*\[{name}\].*"):
            merge_typesystems(base, ts)


@pytest.mark.filterwarnings("ignore:Feature with name")
def test_that_merging_types_with_different_compatible_supertypes_works():
    ts1 = TypeSystem()
    ts1.create_type("test.Sub", description="Example type.", supertypeName="uima.tcas.Annotation")

    ts2 = TypeSystem()
    ts2.create_type("test.Super", description="Example type.", supertypeName="uima.tcas.Annotation")
    ts2.create_type("test.Sub", description="Example type.", supertypeName="test.Super")

    result = merge_typesystems(ts1, ts2)
    sub = result.get_type("test.Sub")

    assert sub.supertype.name == "test.Super"

    # Also check the other order
    result = merge_typesystems(ts2, ts1)
    sub = result.get_type("test.Sub")

    assert sub.supertype.name == "test.Super"


@pytest.mark.filterwarnings("ignore:Feature with name")
def test_that_merging_types_with_different_incompatible_supertypes_throws():
    ts1 = TypeSystem()
    ts1.create_type("test.Sub", description="Example type.", supertypeName="uima.cas.EmptyIntegerList")

    ts2 = TypeSystem()
    ts2.create_type("test.Sub", description="Example type.", supertypeName="uima.cas.NonEmptyStringList")

    with pytest.raises(ValueError, match=r".*incompatible super types.*"):
        merge_typesystems(ts1, ts2)


def test_that_merging_types_creates_self_contained_type_system():
    ts1 = TypeSystem()
    type_a = ts1.create_type(name="example.TypeA")
    type_b = ts1.create_type(name="example.TypeB")
    type_c = ts1.create_type(name="example.TypeC", supertypeName="example.TypeA")
    ts1.create_feature(domainType=type_a, name="typeB", rangeType=type_b)
    ts1.create_feature(domainType=type_b, name="typeA", rangeType=type_a)

    ts2 = TypeSystem()

    ts_merged = merge_typesystems(ts1, ts2)

    merged_type_a = ts_merged.get_type("example.TypeA")
    merged_type_b = ts_merged.get_type("example.TypeB")
    merged_type_c = ts_merged.get_type("example.TypeC")

    assert merged_type_a is not None
    assert merged_type_a.get_feature("typeB") is not type_a.get_feature("typeB")
    assert merged_type_a.get_feature("typeB").rangeType is merged_type_b
    assert merged_type_a.get_feature("typeB").rangeType is not type_b
    assert merged_type_b is not None
    assert merged_type_b.get_feature("typeA") is not type_b.get_feature("typeA")
    assert merged_type_b.get_feature("typeA").rangeType is merged_type_a
    assert merged_type_b.get_feature("typeA").rangeType is not type_a
    assert merged_type_c is not None
    assert merged_type_c.supertype is merged_type_a
    assert merged_type_c.supertype is not type_c


# DKPro Core Support


def test_that_dkpro_core_typeystem_can_be_loaded():
    ts = load_dkpro_core_typesystem()

    POS = ts.get_type("de.tudarmstadt.ukp.dkpro.core.api.lexmorph.type.pos.POS")
    NamedEntity = ts.get_type("de.tudarmstadt.ukp.dkpro.core.api.ner.type.NamedEntity")
    CoreferenceLink = ts.get_type("de.tudarmstadt.ukp.dkpro.core.api.coref.type.CoreferenceLink")


# Type checking
def test_typchecking_fs_array():
    cas = Cas()
    MyValue = cas.typesystem.create_type(name="test.MyValue", supertypeName="uima.cas.TOP")
    MyOtherValue = cas.typesystem.create_type(name="test.MyOtherValue", supertypeName="uima.cas.TOP")
    MyCollection = cas.typesystem.create_type("test.MyCollection", supertypeName="uima.cas.TOP")
    FSArray = cas.typesystem.get_type("uima.cas.FSArray")

    cas.typesystem.create_feature(domainType=MyValue, name="value", rangeType="uima.cas.String")
    cas.typesystem.create_feature(
        domainType=MyCollection, name="members", rangeType="uima.cas.FSArray", elementType="test.MyValue"
    )

    members = FSArray(elements=[MyValue(value="foo"), MyValue(value="bar"), MyOtherValue()])

    collection = MyCollection(members=members)

    cas.add(collection)

    errors = cas.typecheck()

    assert len(errors) == 1
    expected_error = TypeCheckError(
        2, "Member of [uima.cas.FSArray] has unsound type: was [test.MyOtherValue], need [test.MyValue]!"
    )
    assert errors[0] == expected_error


# Getting/Setting with path selector


def test_get_set_path_semargs(cas_with_references_xmi, webanno_typesystem_xml):
    typesystem = load_typesystem(webanno_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_references_xmi, typesystem=typesystem)

    result = cas.select("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemPred")
    assert len(result) == 1
    pred = result[0]
    first_arg = pred.arguments.elements[0]

    assert first_arg.get("target.end") == 5
    first_arg.set("target.end", 42)
    assert first_arg.get("target.end") == 42

    assert first_arg["target.end"] == 42
    first_arg["target.end"] = 23
    assert first_arg["target.end"] == 23


def test_get_set_path_stringlist():
    cas = Cas()

    NonEmptyStringList = cas.typesystem.get_type("uima.cas.NonEmptyStringList")
    EmptyStringList = cas.typesystem.get_type("uima.cas.EmptyStringList")

    data = ["foo", "bar", "baz"]
    lst = NonEmptyStringList()

    cur = lst
    for s in data:
        cur.head = s
        cur.tail = NonEmptyStringList()
        cur = cur.tail
    cur.tail = EmptyStringList()

    assert lst.get("head") == "foo"
    assert lst.get("tail.head") == "bar"
    assert lst.get("tail.tail.head") == "baz"
    assert lst.get("tail.tail.tail.head") is None

    assert lst["head"] == "foo"
    assert lst["tail.head"] == "bar"
    assert lst["tail.tail.head"] == "baz"
    assert lst["tail.tail.tail.head"] is None

    lst.set("head", "new_foo")
    lst.set("tail.head", "new_bar")
    lst.set("tail.tail.head", "new_baz")

    assert lst.get("head") == "new_foo"
    assert lst.get("tail.head") == "new_bar"
    assert lst.get("tail.tail.head") == "new_baz"

    lst["head"] = "newer_foo"
    lst["tail.head"] = "newer_bar"
    lst["tail.tail.head"] = "newer_baz"

    assert lst["head"] == "newer_foo"
    assert lst["tail.head"] == "newer_bar"
    assert lst["tail.tail.head"] == "newer_baz"


def test_set_path_not_found(cas_with_references_xmi, webanno_typesystem_xml):
    typesystem = load_typesystem(webanno_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_references_xmi, typesystem=typesystem)

    result = cas.select("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemPred")
    assert len(result) == 1
    pred = result[0]
    first_arg = pred.arguments.elements[0]

    with pytest.raises(AttributeError):
        first_arg.set("target.bar", 42)


def test_bad_feature_path(small_typesystem_xml):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    TokenType = cas.typesystem.get_type("cassis.Token")
    token = TokenType(xmiID=10, begin=0, end=0)

    with pytest.raises(AttributeError) as ex:
        token[0]

    assert "must be a string" in str(ex.value)


def test_cannot_extend_final_type():
    cas = Cas()

    for type in cas.typesystem.get_types(built_in=True):
        if type.name.endswith("Array"):
            with pytest.raises(ValueError):
                cas.typesystem.create_type("ArraySubType", "uima.cas.IntegerArray")


def test_create_same_type_twice_fails():
    typesystem = TypeSystem()
    typesystem.create_type("my.Type")
    with pytest.raises(ValueError):
        typesystem.create_type("my.Type")


def test_transitive_closure():
    typesystem = TypeSystem()
    base_type = typesystem.create_type("BaseType", supertypeName=TYPE_NAME_ANNOTATION)
    child_type = typesystem.create_type("ChildType", supertypeName="BaseType")
    typesystem.create_feature("ChildType", "primitiveFeature", TYPE_NAME_STRING)
    typesystem.create_feature("ChildType", "arrayFeature", TYPE_NAME_STRING_ARRAY, elementType=TYPE_NAME_STRING)
    typesystem.create_feature("ChildType", "fsFeature", "BaseType")

    transitive_closure_without_builtins = typesystem.transitive_closure({child_type}, built_in=False)

    assert transitive_closure_without_builtins == {base_type, child_type}

    transitive_closure_with_builtins = typesystem.transitive_closure({child_type}, built_in=True)

    assert transitive_closure_with_builtins == {
        base_type,
        child_type,
        typesystem.get_type(TYPE_NAME_TOP),
        typesystem.get_type(TYPE_NAME_ANNOTATION_BASE),
        typesystem.get_type(TYPE_NAME_ANNOTATION),
        typesystem.get_type(TYPE_NAME_STRING),
        typesystem.get_type(TYPE_NAME_ARRAY_BASE),
        typesystem.get_type(TYPE_NAME_STRING_ARRAY),
        typesystem.get_type(TYPE_NAME_INTEGER),
        typesystem.get_type(TYPE_NAME_SOFA),
    }
