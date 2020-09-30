import warnings
from pathlib import Path

import pytest

from cassis import TypeSystem, load_typesystem
from cassis.typesystem import _COLLECTION_TYPES, TOP_TYPE_NAME, Feature, TypeCheckError
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


def test_feature_can_be_added():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    typesystem.add_feature(type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature")

    actual_type = typesystem.get_type("test.Type")
    actual_feature = actual_type.get_feature("testFeature")
    assert actual_feature.name == "testFeature"
    assert actual_feature.rangeTypeName == "String"
    assert actual_feature.description == "A test feature"


def test_feature_adding_warns_if_redefined_identically():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")

    typesystem.add_feature(type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature")
    with pytest.warns(UserWarning):
        typesystem.add_feature(
            type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature"
        )


def test_feature_adding_throws_if_redefined_differently():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name="test.Type")
    typesystem.add_feature(type_=test_type, name="testFeature", rangeTypeName="String", description="A test feature")

    with pytest.raises(ValueError):
        typesystem.add_feature(
            type_=test_type, name="testFeature", rangeTypeName="Boolean", description="A test feature"
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

    with open(path, "r") as f:
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
    feature = Feature("test_feature", rangeTypeName=feature_name)
    t.add_feature(feature)

    assert typesystem.is_collection(type_name, feature) == expected


@pytest.mark.parametrize("type_name", [c for c in _COLLECTION_TYPES])
def test_is_collection_for_builtin_collections_with_elements(type_name: str):
    typesystem = TypeSystem()
    t = typesystem.get_type(type_name)
    feature = Feature("elements", rangeTypeName="uima.cas.TOP")

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
    assert ts.subsumes(parent_name, child_name) == expected


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


@pytest.mark.parametrize("typesystem_xml", TYPESYSTEM_FIXTURES)
def test_serializing_typesystem_to_file_path(tmpdir, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    path = Path(str(tmpdir.join("typesystem.xml")))

    typesystem.to_xml(path)

    with path.open("rb") as actual:
        assert_xml_equal(actual, typesystem_xml)


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
    with open(typesystem_merge_base_path(), "r") as f:
        base = load_typesystem(f.read())

    ts = TypeSystem()
    t = ts.create_type("test.ArraysAndListsWithElementTypes", supertypeName="uima.cas.TOP")
    ts.add_feature(
        type_=t,
        name=name,
        rangeTypeName=rangeTypeName,
        elementType=elementType,
        multipleReferencesAllowed=multipleReferencesAllowed,
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)

        result = merge_typesystems(base, ts)

    assert result.contains_type("test.ArraysAndListsWithElementTypes")


@pytest.mark.parametrize(
    "name, rangeTypeName, elementType, multipleReferencesAllowed",
    [
        ("arrayNoElementType", "uima.cas.FSArray", "uima.tcas.Annotation", None),  # Different elementTypes
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.cas.AnnotationBase", True),  # Different elementTypes
        ("arrayMultiRefsOk", "uima.cas.FSList", "uima.cas.Annotation", True),  # Incompatible rangeTypes
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.cas.Annotation", False),  # Different multiref
        ("arrayNoMultiRefs", "uima.cas.FSArray", "uima.cas.Annotation", True),  # Different multiref
        ("arrayMultiRefsOk", "uima.cas.FSArray", "uima.cas.Annotation", None),  # Different multiref default
    ],
)
def test_that_merging_incompatible_typesystem_throws(name, rangeTypeName, elementType, multipleReferencesAllowed):
    with open(typesystem_merge_base_path(), "r") as f:
        base = load_typesystem(f.read())

    ts = TypeSystem()
    t = ts.create_type("test.ArraysAndListsWithElementTypes", supertypeName="uima.cas.TOP")
    ts.add_feature(
        type_=t,
        name=name,
        rangeTypeName=rangeTypeName,
        elementType=elementType,
        multipleReferencesAllowed=multipleReferencesAllowed,
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with pytest.raises(ValueError, match=r".*\[{0}\].*".format(name)):
            merge_typesystems(base, ts)


def test_that_merging_types_with_different_compatible_supertypes_works():
    ts1 = TypeSystem()
    ts1.create_type("test.Sub", description="Example type.", supertypeName="uima.tcas.Annotation")

    ts2 = TypeSystem()
    ts2.create_type("test.Super", description="Example type.", supertypeName="uima.tcas.Annotation")
    ts2.create_type("test.Sub", description="Example type.", supertypeName="test.Super")

    result = merge_typesystems(ts1, ts2)
    sub = result.get_type("test.Sub")

    assert sub.supertypeName == "test.Super"

    # Also check the other order
    result = merge_typesystems(ts2, ts1)
    sub = result.get_type("test.Sub")

    assert sub.supertypeName == "test.Super"


def test_that_merging_types_with_different_incompatible_supertypes_throws():
    ts1 = TypeSystem()
    ts1.create_type("test.Sub", description="Example type.", supertypeName="uima.cas.EmptyIntegerList")

    ts2 = TypeSystem()
    ts2.create_type("test.Sub", description="Example type.", supertypeName="uima.cas.NonEmptyStringList")

    with pytest.raises(ValueError, match=r".*incompatible super types.*"):
        merge_typesystems(ts1, ts2)


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

    cas.typesystem.add_feature(type_=MyValue, name="value", rangeTypeName="uima.cas.String")
    cas.typesystem.add_feature(
        type_=MyCollection, name="members", rangeTypeName="uima.cas.FSArray", elementType="test.MyValue"
    )

    members = [MyValue(value="foo"), MyValue(value="bar"), MyOtherValue()]

    collection = MyCollection(members=members)

    cas.add_annotation(collection)

    errors = cas.typecheck()

    assert len(errors) == 1
    expected_error = TypeCheckError(
        2, "Member of [uima.cas.FSArray] has unsound type: was [test.MyOtherValue], need [test.MyValue]!"
    )
    assert errors[0] == expected_error
