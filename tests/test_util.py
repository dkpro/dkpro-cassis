from cassis.typesystem import TYPE_NAME_ANNOTATION, TYPE_NAME_FS_ARRAY
from tests.fixtures import *
from tests.test_files.test_cas_generators import MultiFeatureRandomCasGenerator, MultiTypeRandomCasGenerator
from pytest_lazy_fixtures import lf


FIXTURES = [
    (lf("small_xmi"), lf("small_typesystem_xml")),
    (lf("cas_with_inheritance_xmi"), lf("typesystem_with_inheritance_xml")),
    (lf("cas_with_collections_xmi"), lf("typesystem_with_collections_xml")),
    (lf("cas_with_references_xmi"), lf("webanno_typesystem_xml")),
    (lf("cas_with_nonindexed_fs_xmi"), lf("dkpro_typesystem_xml")),
    (lf("cas_with_empty_array_references_xmi"), lf("dkpro_typesystem_xml")),
    (lf("cas_with_reserved_names_xmi"), lf("typesystem_with_reserved_names_xml")),
    (lf("cas_with_two_sofas_xmi"), lf("small_typesystem_xml")),
    (lf("cas_with_smileys_xmi"), lf("dkpro_typesystem_xml")),
    (
        lf("cas_with_floating_point_special_values_xmi"),
        lf("typesystem_with_floating_points_xml"),
    ),
    (
        lf("cas_has_fs_with_no_namespace_xmi"),
        lf("typesystem_has_types_with_no_namespace_xml"),
    ),
    (
        lf("cas_with_multiple_references_allowed_string_array_xmi"),
        lf("typesystem_with_multiple_references_allowed_xml"),
    ),
]


def test_cas_to_comparable_text_on_minimal_cas():
    cas = Cas()
    cas.sofa_string = "ABCDE"
    Annotation = cas.typesystem.get_type(TYPE_NAME_ANNOTATION)
    for i in range(0, 5):
        cas.add(Annotation(begin=i, end=i + 1))

    expected = (
        '"uima.tcas.Annotation"\n'
        '"<ANCHOR>","<COVERED_TEXT>"\n'
        '"Annotation[0-1]*@_InitialView","A"\n'
        '"Annotation[1-2]*@_InitialView","B"\n'
        '"Annotation[2-3]*@_InitialView","C"\n'
        '"Annotation[3-4]*@_InitialView","D"\n'
        '"Annotation[4-5]*@_InitialView","E"\n'
    )

    assert cas_to_comparable_text(cas) == expected


def test_cas_to_comparable_text_on_multi_feature_random():
    generator = MultiFeatureRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_fs()) for view in randomized_cas.views)}")
        cas_to_comparable_text(randomized_cas)
        # At this point, we are just testing if there is no exception during rendering


def test_cas_to_comparable_text_on_multi_type_random():
    generator = MultiTypeRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_fs()) for view in randomized_cas.views)}")
        cas_to_comparable_text(randomized_cas)
        # At this point, we are just testing if there is no exception during rendering


def test_cas_to_comparable_text_excluding_types():
    typesystem = TypeSystem()
    TypeA = typesystem.create_type("type.A", supertypeName=TYPE_NAME_ANNOTATION)
    TypeB = typesystem.create_type("type.B", supertypeName=TYPE_NAME_ANNOTATION)
    cas = Cas(typesystem=typesystem)
    cas.sofa_string = "ABCDE"
    for i in range(0, 5):
        cas.add(TypeA(begin=i, end=i + 1))
        cas.add(TypeB(begin=i, end=i + 1))

    expected = (
        '"type.A"\n'
        '"<ANCHOR>","<COVERED_TEXT>"\n'
        '"A[0-1]*@_InitialView","A"\n'
        '"A[1-2]*@_InitialView","B"\n'
        '"A[2-3]*@_InitialView","C"\n'
        '"A[3-4]*@_InitialView","D"\n'
        '"A[4-5]*@_InitialView","E"\n'
    )

    assert cas_to_comparable_text(cas, exclude_types=[TypeB.name]) == expected


def test_cas_to_comparable_text_orders_same_location_annotations_deterministically():
    typesystem = TypeSystem()
    Foo = typesystem.create_type("type.Foo", supertypeName=TYPE_NAME_ANNOTATION)
    typesystem.create_feature(name="value", domainType=Foo, rangeType="uima.cas.String")

    cas = Cas(typesystem=typesystem)
    cas.sofa_string = "ABCDE"
    cas.add(Foo(begin=0, end=1, value="b"))
    cas.add(Foo(begin=0, end=1, value="a"))

    expected = (
        '"type.Foo"\n'
        '"<ANCHOR>","<COVERED_TEXT>","value"\n'
        '"Foo[0-1]*@_InitialView","A","a"\n'
        '"Foo[0-1]*@_InitialView(1)","A","b"\n'
    )

    assert cas_to_comparable_text(cas) == expected


def test_cas_to_comparable_text_with_null_arrays():
    typesystem = TypeSystem()
    FSArray = typesystem.get_type(TYPE_NAME_FS_ARRAY)
    ArrayHolder = typesystem.create_type("type.ArrayHolder", supertypeName=TYPE_NAME_ANNOTATION)
    typesystem.create_feature(
        name="array", domainType=ArrayHolder, rangeType=TYPE_NAME_FS_ARRAY, elementType=TYPE_NAME_ANNOTATION
    )
    cas = Cas(typesystem=typesystem)
    cas.sofa_string = "ABCDE"
    cas.add(ArrayHolder(begin=0, end=5, array=FSArray(elements=None)))
    cas_to_comparable_text(cas)


@pytest.mark.filterwarnings("ignore:Trying to add feature")
@pytest.mark.parametrize("xmi, typesystem_xml", FIXTURES)
def test_cas_to_comparable_text_on_fixtures(xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)

    cas_to_comparable_text(cas)
