from cassis.typesystem import TYPE_NAME_ANNOTATION
from tests.fixtures import *
from tests.test_files.test_cas_generators import MultiFeatureRandomCasGenerator, MultiTypeRandomCasGenerator


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
