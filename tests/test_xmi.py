import warnings
from pathlib import Path

from lxml import etree

from cassis.typesystem import TYPE_NAME_ANNOTATION, TYPE_NAME_SOFA, TypeNotFoundError
from tests.fixtures import *
from tests.test_files.test_cas_generators import (
    MultiFeatureRandomCasGenerator,
    MultiTypeRandomCasGenerator,
    StringArrayMode,
)
from tests.util import assert_xml_equal

# Deserializing

FIXTURES = [
    (pytest.lazy_fixture("small_xmi"), pytest.lazy_fixture("small_typesystem_xml")),
    (pytest.lazy_fixture("cas_with_inheritance_xmi"), pytest.lazy_fixture("typesystem_with_inheritance_xml")),
    (pytest.lazy_fixture("cas_with_collections_xmi"), pytest.lazy_fixture("typesystem_with_collections_xml")),
    (pytest.lazy_fixture("cas_with_references_xmi"), pytest.lazy_fixture("webanno_typesystem_xml")),
    (pytest.lazy_fixture("cas_with_nonindexed_fs_xmi"), pytest.lazy_fixture("dkpro_typesystem_xml")),
    (pytest.lazy_fixture("cas_with_empty_array_references_xmi"), pytest.lazy_fixture("dkpro_typesystem_xml")),
    (pytest.lazy_fixture("cas_with_reserved_names_xmi"), pytest.lazy_fixture("typesystem_with_reserved_names_xml")),
    (pytest.lazy_fixture("cas_with_two_sofas_xmi"), pytest.lazy_fixture("small_typesystem_xml")),
    (pytest.lazy_fixture("cas_with_smileys_xmi"), pytest.lazy_fixture("dkpro_typesystem_xml")),
    (
        pytest.lazy_fixture("cas_with_floating_point_special_values_xmi"),
        pytest.lazy_fixture("typesystem_with_floating_points_xml"),
    ),
    (
        pytest.lazy_fixture("cas_has_fs_with_no_namespace_xmi"),
        pytest.lazy_fixture("typesystem_has_types_with_no_namespace_xml"),
    ),
    (
        pytest.lazy_fixture("cas_with_multiple_references_allowed_string_array_xmi"),
        pytest.lazy_fixture("typesystem_with_multiple_references_allowed_xml"),
    ),
    (
        pytest.lazy_fixture("cas_with_list_features_xmi"),
        pytest.lazy_fixture("typesystem_with_list_features_xml"),
    ),
    (
        pytest.lazy_fixture("cas_with_array_features_xmi"),
        pytest.lazy_fixture("typesystem_with_array_features_xml"),
    ),
]


def test_deserializing_from_file(small_xmi_path, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    with open(small_xmi_path, "rb") as f:
        load_cas_from_xmi(f, typesystem=typesystem)


def test_deserializing_from_string(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas_xmi = """<?xml version="1.0" encoding="UTF-8"?>
    <xmi:XMI xmlns:tcas="http:///uima/tcas.ecore" xmlns:xmi="http://www.omg.org/XMI" xmlns:cas="http:///uima/cas.ecore"
             xmlns:cassis="http:///cassis.ecore" xmi:version="2.0">
        <cas:NULL xmi:id="0"/>
        <tcas:DocumentAnnotation xmi:id="8" sofa="1" begin="0" end="47" language="x-unspecified"/>
        <cassis:Sentence xmi:id="79" sofa="1" begin="0" end="26" id="0"/>
        <cassis:Sentence xmi:id="84" sofa="1" begin="27" end="47" id="1"/>
        <cas:Sofa xmi:id="1" sofaNum="1" sofaID="mySofa" mimeType="text/plain"
                  sofaString="Joe waited for the train . The train was late ."/>
        <cas:View sofa="1" members="8 79 84"/>
    </xmi:XMI>    
    """
    load_cas_from_xmi(cas_xmi, typesystem=typesystem)


def test_sofas_are_parsed(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem)

    expected_sofas = [
        Sofa(
            type=typesystem.get_type(TYPE_NAME_SOFA),
            xmiID=15,
            sofaNum=1,
            sofaID="_InitialView",
            mimeType="text/plain",
            sofaString="Joe waited for the train . The train was late .",
        )
    ]
    assert expected_sofas == cas.sofas


def test_views_are_parsed(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas_xmi = """<?xml version="1.0" encoding="UTF-8"?>
    <xmi:XMI xmlns:tcas="http:///uima/tcas.ecore" xmlns:xmi="http://www.omg.org/XMI" xmlns:cas="http:///uima/cas.ecore"
             xmlns:cassis="http:///cassis.ecore" xmi:version="2.0">
        <cas:NULL xmi:id="0"/>
        <tcas:DocumentAnnotation xmi:id="8" sofa="1" begin="0" end="26" language="x-unspecified"/>
        <cassis:Sentence xmi:id="79" sofa="1" begin="0" end="26" id="0"/>
        <cassis:Sentence xmi:id="84" sofa="2" begin="0" end="20" id="1"/>
        <cas:Sofa xmi:id="1" sofaNum="1" sofaID="sofa1" mimeType="text/plain"
                  sofaString="Joe waited for the train ."/>
        <cas:View sofa="1" members="8 79"/>
        <cas:Sofa xmi:id="2" sofaNum="2" sofaID="sofa2" mimeType="text/plain"
                  sofaString="The train was late ."/>
        <cas:View sofa="2" members="84"/>
    </xmi:XMI>    
    """
    cas = load_cas_from_xmi(cas_xmi, typesystem=typesystem)

    view1 = cas.get_view("sofa1")
    view2 = cas.get_view("sofa2")
    assert 2 == len(list(view1.select_all()))
    assert 1 == len(list(view2.select_all()))


def test_deserializing_and_then_adding_annotations_works(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    TokenType = typesystem.get_type("cassis.Token")

    cas = load_cas_from_xmi(small_xmi, typesystem=typesystem)
    cas.add(TokenType(begin=0, end=3, id="0", pos="NNP"))

    # Check that serializing still works
    xmi = cas.to_xmi()
    load_cas_from_xmi(xmi, typesystem=typesystem)

    # Check that view contains unique ids
    root = etree.fromstring(xmi.encode("utf-8"))
    member_ids = [0]
    fs_ids = []
    for view in root.xpath("//cas:View", namespaces=root.nsmap):
        member_ids.extend([int(x) for x in view.attrib["members"].split(" ")])
        member_ids.append(int(view.attrib["sofa"]))

    for xmi_id in root.xpath("//@xmi:id", namespaces=root.nsmap):
        fs_ids.append(int(xmi_id))

    assert len(set(member_ids)) == len(member_ids)
    assert len(set(fs_ids)) == len(fs_ids)
    assert set(member_ids) == set(fs_ids)


def test_deserializing_references_in_attributes_work(cas_with_references_xmi, webanno_typesystem_xml):
    typesystem = load_typesystem(webanno_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_references_xmi, typesystem=typesystem)

    tokens = list(cas.select("de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token"))
    assert len(tokens) == 6

    # Retrieve semantic predicates
    sempreds = list(cas.select("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemPred"))
    assert len(sempreds) == 1
    sempred = sempreds[0]

    # Retrieve semantic arguments
    semargs = list(cas.select("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemArg"))
    assert len(semargs) == 2

    # Retrieve semantic argument links
    semarglinks = list(cas.select("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemArgLink"))
    assert len(semarglinks) == 2

    # Check that the references to the semantic argument links have been resolved
    assert sempred.arguments.elements == semarglinks

    # Check that the references from the links to the arguments have been resolved
    assert semarglinks[0].target == semargs[0]
    assert semarglinks[1].target == semargs[1]


# Serializing


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("xmi, typesystem_xml", FIXTURES)
def test_serializing_cas_to_string(xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)

    actual_xml = cas.to_xmi()

    assert_xml_equal(actual_xml, xmi)


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("xmi, typesystem_xml", FIXTURES)
def test_serializing_cas_to_file_path(tmpdir, xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)
    path = str(tmpdir.join("cas.xml"))

    cas.to_xmi(path)

    with open(path) as actual:
        assert_xml_equal(actual.read(), xmi)


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("xmi, typesystem_xml", FIXTURES)
def test_serializing_cas_to_file(tmpdir, xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)
    path = Path(str(tmpdir.join("cas.xml")))

    cas.to_xmi(path)

    with path.open("r") as actual:
        assert_xml_equal(actual.read(), xmi)


def test_serializing_xmi_has_correct_namespaces(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem=typesystem)

    actual_xml = cas.to_xmi()

    assert_xml_equal(actual_xml, small_xmi)
    # Assert that the namespace is only once fully specified
    assert actual_xml.count('xmlns:cas="http:///uima/cas.ecore"') == 1
    assert actual_xml.count("ns0") == 0


def test_serializing_xmi_ignores_none_features(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem=typesystem)
    TokenType = typesystem.get_type("cassis.Token")
    cas.add(TokenType(begin=0, end=3, id=None, pos=None))

    actual_xml = cas.to_xmi()

    assert actual_xml.count('"None') == 0


def test_serializing_xmi_namespaces_with_same_prefixes_but_different_urls_are_disambiguated():
    typesystem = TypeSystem()
    cas = Cas(typesystem)
    FooType = typesystem.create_type("foo.test.Foo")
    BarType = typesystem.create_type("bar.test.Bar")

    # Check that two annotations of the same type get the same namespace
    cas.add(FooType())
    cas.add(BarType())
    cas.add(FooType())
    cas.add(BarType())
    actual_xmi = cas.to_xmi()

    root = etree.fromstring(actual_xmi.encode("utf-8"))
    assert root.nsmap["test"] == "http:///foo/test.ecore"
    assert root.nsmap["test0"] == "http:///bar/test.ecore"
    assert len(root.xpath("//test:Foo", namespaces=root.nsmap)) == 2
    assert len(root.xpath("//test0:Bar", namespaces=root.nsmap)) == 2


def test_serializing_with_unset_xmi_ids_works():
    typesystem = TypeSystem()
    cas = Cas(typesystem)
    FooType = typesystem.create_type("foo.test.Foo")
    BarType = typesystem.create_type("bar.test.Bar")
    typesystem.create_feature(FooType, "bar", "bar.test.Bar")

    # Check that two annotations of the same type get the same namespace
    foo1 = FooType()
    cas.add(foo1)
    foo1.bar = BarType()

    foo2 = FooType()
    cas.add(foo2)
    foo2.bar = BarType()

    # assert no error
    cas.to_xmi(pretty_print=True)


# UIMA vs cassis offsets


def test_offsets_are_mapped_from_uima_to_cassis(cas_with_smileys_xmi, dkpro_typesystem_xml):
    typesystem = load_typesystem(dkpro_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_smileys_xmi, typesystem=typesystem)

    named_entities = cas.select("de.tudarmstadt.ukp.dkpro.core.api.ner.type.NamedEntity")

    surface_forms = [ne.get_covered_text() for ne in named_entities]

    assert surface_forms == ["Transformers", "Transformers", "Transformers", "PyTorch", "TensorFlow"]


def test_offsets_are_recomputed_when_sofa_string_changes(cas_with_smileys_xmi, dkpro_typesystem_xml):
    typesystem = load_typesystem(dkpro_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_smileys_xmi, typesystem=typesystem)

    size_uima_to_cassis_before = len(cas.get_sofa()._offset_converter._external_to_python)
    size_cassis_to_uima_before = len(cas.get_sofa()._offset_converter._python_to_external)

    cas.sofa_string = "Hello 😊, my name is Jan."

    size_uima_to_cassis_after = len(cas.get_sofa()._offset_converter._external_to_python)
    size_cassis_to_uima_after = len(cas.get_sofa()._offset_converter._python_to_external)

    assert size_uima_to_cassis_before != size_uima_to_cassis_after
    assert size_cassis_to_uima_before != size_cassis_to_uima_after


def test_offsets_work_for_empty_sofastring():
    xmi = """<?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmlns:xmi="http://www.omg.org/XMI" xmlns:tcas="http:///uima/tcas.ecore" 
            xmlns:cas="http:///uima/cas.ecore" xmi:version="2.0"> 
            <cas:NULL xmi:id="0" /> 
            <tcas:DocumentAnnotation xmi:id="2" sofa="1" begin="0" end="0" language="en" /> 
            <cas:Sofa xmi:id="1" sofaNum="1" sofaID="_InitialView" mimeType="text" sofaString="" /> 
            <cas:View sofa="1" members="2" />
        </xmi:XMI>"""

    # assert no exception
    load_cas_from_xmi(xmi)


def test_that_invalid_offsets_remain_unmapped_on_import():
    xmi = """<?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmlns:xmi="http://www.omg.org/XMI" xmlns:tcas="http:///uima/tcas.ecore" 
            xmlns:cas="http:///uima/cas.ecore" xmi:version="2.0"> 
            <cas:NULL xmi:id="0" /> 
            <tcas:DocumentAnnotation xmi:id="2" sofa="1" begin="0" end="4" language="en" /> 
            <tcas:Annotation xmi:id="3" sofa="1" begin="100" end="200" /> 
            <cas:Sofa xmi:id="1" sofaNum="1" sofaID="_InitialView" mimeType="text" sofaString="Test" /> 
            <cas:View sofa="1" members="2 3" />
        </xmi:XMI>"""

    # assert no exception
    with warnings.catch_warnings(record=True) as ws:
        cas = load_cas_from_xmi(xmi)

    for w in ws:
        assert str(w.message).startswith("Not mapping external")

    annotations = list(filter(lambda a: a.type.name == TYPE_NAME_ANNOTATION, cas.select(TYPE_NAME_ANNOTATION)))
    assert len(annotations) == 1
    assert annotations[0].begin == 100
    assert annotations[0].end == 200


def test_that_invalid_offsets_remain_unmapped_on_export():
    cas = Cas()
    cas.sofa_string = "Test"
    Annotation = cas.typesystem.get_type(TYPE_NAME_ANNOTATION)
    cas.add(Annotation(begin=100, end=200))

    with warnings.catch_warnings(record=True) as ws:
        xmi = cas.to_xmi()

    for w in ws:
        assert str(w.message).startswith("Not mapping internal")

    assert 'begin="100"' in xmi
    assert 'end="200"' in xmi


# Leniency


def test_leniency_type_not_in_typesystem_lenient(cas_with_leniency_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    with pytest.warns(UserWarning):
        cas = load_cas_from_xmi(cas_with_leniency_xmi, typesystem=typesystem, lenient=True)


def test_leniency_type_not_in_typesystem_not_lenient(cas_with_leniency_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    with pytest.raises(TypeNotFoundError):
        cas = load_cas_from_xmi(cas_with_leniency_xmi, typesystem=typesystem, lenient=False)


def test_multiple_references_allowed_true():
    typesystem = TypeSystem()
    Foo = typesystem.create_type("Foo")
    IntegerArray = typesystem.get_type("uima.cas.IntegerArray")
    f = typesystem.create_feature(Foo, "intArray", "uima.cas.IntegerArray", elementType="uima.cas.Integer")

    cas = Cas(typesystem)
    foo = Foo()
    foo.intArray = IntegerArray(elements=[1, 2, 3])
    cas.add(foo)

    f.multipleReferencesAllowed = None
    actual_xmi = cas.to_xmi(pretty_print=True)
    root = etree.fromstring(actual_xmi.encode("utf-8"))
    assert len(root.xpath("//cas:IntegerArray", namespaces=root.nsmap)) == 0
    assert len(root.xpath("//noNamespace:Foo/@intArray", namespaces=root.nsmap)) == 1

    f.multipleReferencesAllowed = True
    actual_xmi = cas.to_xmi(pretty_print=True)
    root = etree.fromstring(actual_xmi.encode("utf-8"))
    assert len(root.xpath("//cas:IntegerArray", namespaces=root.nsmap)) == 1
    assert root.xpath("//noNamespace:Foo/@intArray", namespaces=root.nsmap) == [f"{foo.intArray.xmiID}"]

    f.multipleReferencesAllowed = False
    actual_xmi = cas.to_xmi(pretty_print=True)
    root = etree.fromstring(actual_xmi.encode("utf-8"))
    assert len(root.xpath("//cas:IntegerArray", namespaces=root.nsmap)) == 0
    assert len(root.xpath("//noNamespace:Foo/@intArray", namespaces=root.nsmap)) == 1


def test_multi_type_random_serialization_deserialization():
    generator = MultiTypeRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        expected_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_annotations()) for view in expected_cas.views)}")

        xmi = expected_cas.to_xmi()
        actual_cas = load_cas_from_xmi(xmi, typesystem)

        actual = cas_to_comparable_text(actual_cas)
        expected = cas_to_comparable_text(expected_cas)
        assert actual == expected


def test_multi_feature_random_serialization_deserialization():
    generator = MultiFeatureRandomCasGenerator()
    generator.string_array_mode = StringArrayMode.EMPTY_STRINGS_AS_NULL
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        expected_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_annotations()) for view in expected_cas.views)}")

        xmi = expected_cas.to_xmi()
        actual_cas = load_cas_from_xmi(xmi, typesystem)

        actual = cas_to_comparable_text(actual_cas)
        expected = cas_to_comparable_text(expected_cas)
        assert actual == expected
