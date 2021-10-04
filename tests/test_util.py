from pathlib import Path

from cassis.typesystem import TYPE_NAME_ANNOTATION, TYPE_NAME_FS_ARRAY
from tests.fixtures import *
from tests.test_files.test_cas_generators import MultiFeatureRandomCasGenerator, MultiTypeRandomCasGenerator

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
]


def test_cas_to_comparable_text_on_minimal_cas():
    cas = Cas()
    cas.sofa_string = "ABCDE"
    Annotation = cas.typesystem.get_type(TYPE_NAME_ANNOTATION)
    for i in range(0, 5):
        cas.add(Annotation(begin=i, end=i + 1))

    expected = (
        '"uima.tcas.Annotation"\n'
        '"<ANCHOR>","<COVERED_TEXT>","begin","end"\n'
        '"Annotation[0-1]*@_InitialView","A","0","1"\n'
        '"Annotation[1-2]*@_InitialView","B","1","2"\n'
        '"Annotation[2-3]*@_InitialView","C","2","3"\n'
        '"Annotation[3-4]*@_InitialView","D","3","4"\n'
        '"Annotation[4-5]*@_InitialView","E","4","5"\n'
    )

    assert cas_to_comparable_text(cas) == expected


def test_cas_to_comparable_text_on_multi_feature_random():
    generator = MultiFeatureRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_annotations()) for view in randomized_cas.views)}")
        cas_to_comparable_text(randomized_cas)
        # At this point, we are just testing if there is no exception during rendering


def test_cas_to_comparable_text_on_multi_type_random():
    generator = MultiTypeRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_annotations()) for view in randomized_cas.views)}")
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
        '"<ANCHOR>","<COVERED_TEXT>","begin","end"\n'
        '"A[0-1]*@_InitialView","A","0","1"\n'
        '"A[1-2]*@_InitialView","B","1","2"\n'
        '"A[2-3]*@_InitialView","C","2","3"\n'
        '"A[3-4]*@_InitialView","D","3","4"\n'
        '"A[4-5]*@_InitialView","E","4","5"\n'
    )

    assert cas_to_comparable_text(cas, exclude_types=[TypeB.name]) == expected


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
