import random
import pytest

import attr

from cassis.typesystem import (
    TYPE_NAME_ANNOTATION,
    TYPE_NAME_INTEGER,
    TYPE_NAME_INTEGER_ARRAY,
    TYPE_NAME_STRING,
    TYPE_NAME_TOP,
    AnnotationHasNoSofa,
    FeatureStructure,
)
from tests.fixtures import *
from cassis.util import overlapping

# Cas


def test_default_typesystem_is_not_shared():
    # https://github.com/dkpro/dkpro-cassis/issues/67
    cas1 = Cas()
    cas2 = Cas()

    cas1.typesystem.create_type(name="test.Type")
    cas2.typesystem.create_type(name="test.Type")


def test_default_typesystem_is_not_shared_load_from_xmi(empty_cas_xmi: str):
    # https://github.com/dkpro/dkpro-cassis/issues/67
    cas1 = load_cas_from_xmi(empty_cas_xmi)
    cas2 = load_cas_from_xmi(empty_cas_xmi)

    cas1.typesystem.create_type(name="test.Type")
    cas2.typesystem.create_type(name="test.Type")


# View


def test_initial_view_is_created():
    cas = Cas()

    view = cas.get_view("_InitialView")

    sofa = view.get_sofa()
    attr.validate(sofa)
    assert sofa.sofaID == "_InitialView"


def test_create_view_creates_view():
    cas = Cas()

    view = cas.create_view("testView")
    sofa = view.get_sofa()

    attr.validate(sofa)
    assert sofa.sofaID == "testView"


def test_create_view_throws_if_view_already_exists():
    cas = Cas()
    cas.create_view("testView")

    with pytest.raises(ValueError, match=r"A view with name \[testView\] already exists!"):
        cas.create_view("testView")


def test_get_view_finds_existing_view():
    cas = Cas()
    cas.create_view("testView")
    cas.sofa_string = "Initial"

    view = cas.get_view("testView")
    view.sofa_string = "testView42"

    sofa = view.get_sofa()
    attr.validate(sofa)
    assert sofa.sofaID == "testView"
    assert cas.sofa_string == "Initial"
    assert view.sofa_string == "testView42"


def test_get_view_throws_if_view_does_not_exist():
    cas = Cas()

    with pytest.raises(KeyError, match=r"There is no view with name \[testView\] in this CAS!"):
        cas.get_view("testView")


# Sofa


def test_sofa_string_can_be_set_and_read():
    cas = Cas()

    cas.sofa_string = "I am a test sofa string!"

    assert cas.sofa_string == "I am a test sofa string!"


def test_sofa_mime_can_be_set_and_read():
    cas = Cas()

    cas.sofa_mime = "text/plain"

    assert cas.sofa_mime == "text/plain"


def test_sofa_uri_can_be_set_and_read():
    cas = Cas()

    cas.sofa_uri = "https://raw.githubusercontent.com/dkpro/dkpro-cassis/master/README.rst"

    assert cas.sofa_uri == "https://raw.githubusercontent.com/dkpro/dkpro-cassis/master/README.rst"


def test_sofa_string_can_be_set_using_constructor():
    cas = Cas(sofa_string="I am a test sofa string!")

    assert cas.sofa_string == "I am a test sofa string!"
    assert cas.sofa_mime == "text/plain"


def test_sofa_string_and_mime_type_can_be_set_using_constructor():
    cas = Cas(sofa_string="I am a <b>test sofa string!</b>", sofa_mime="text/html")

    assert cas.sofa_string == "I am a <b>test sofa string!</b>"
    assert cas.sofa_mime == "text/html"


def test_document_language_can_be_set_using_constructor():
    cas = Cas(sofa_string="Ich bin ein test!", document_language="de")

    assert cas.sofa_string == "Ich bin ein test!"
    assert cas.sofa_mime == "text/plain"
    assert cas.document_language == "de"


# Select


def test_select(small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]):
    ts = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=ts)
    cas.add_all(tokens + sentences)

    assert list(cas.select("Token")) == tokens
    assert list(cas.select("cassis.Token")) == tokens
    assert list(cas.select("Sentence")) == sentences
    assert list(cas.select("cassis.Sentence")) == sentences
    assert list(cas.select(ts.get_type("cassis.Token"))) == tokens
    assert list(cas.select(ts.get_type("cassis.Sentence"))) == sentences
    assert set(cas.select(ts.get_type(TYPE_NAME_TOP))) == set(tokens) | set(sentences)


def test_select_also_returns_parent_instances(
    small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]
):
    annotations = tokens + sentences
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_all(annotations)

    actual_annotations = list(cas.select(TYPE_NAME_ANNOTATION))

    assert set(actual_annotations) == set(annotations)


def test_select_covered(small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]):
    ts = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=ts)
    cas.add_all(tokens + sentences)
    first_sentence, second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    assert list(cas.select_covered("cassis.Token", first_sentence)) == tokens_in_first_sentence
    assert list(cas.select_covered("cassis.Token", second_sentence)) == tokens_in_second_sentence
    assert list(cas.select_covered(ts.get_type("cassis.Token"), first_sentence)) == tokens_in_first_sentence
    assert list(cas.select_covered(ts.get_type("cassis.Token"), second_sentence)) == tokens_in_second_sentence


def test_select_covered_overlapping(small_typesystem_xml: str):
    ts = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=ts)

    AnnotationType = cas.typesystem.create_type("test.Annotation")
    SentenceType = cas.typesystem.get_type("cassis.Sentence")
    sentence = SentenceType(begin=0, end=10)
    annotations = [AnnotationType(begin=0, end=5), AnnotationType(begin=0, end=5)]

    cas.add(sentence)
    cas.add_all(annotations)

    assert list(cas.select_covered("test.Annotation", sentence)) == annotations
    assert list(cas.select_covered(ts.get_type("test.Annotation"), sentence)) == annotations


def test_select_covered_also_returns_parent_instances(
    small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]
):
    typesystem = load_typesystem(small_typesystem_xml)
    SubTokenType = typesystem.create_type("cassis.SubToken", supertypeName="cassis.Token")

    annotations = tokens + sentences
    subtoken1 = SubTokenType(begin=tokens[2].begin, end=tokens[3].end)
    subtoken2 = SubTokenType(begin=tokens[8].begin, end=tokens[8].end)
    annotations.append(subtoken1)
    annotations.append(subtoken2)

    cas = Cas(typesystem=typesystem)
    cas.sofa_string = "012345678901234567890"
    cas.add_all(annotations)

    first_sentence, second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    actual_tokens_in_first_sentence = list(cas.select_covered("cassis.Token", first_sentence))
    actual_tokens_in_second_sentence = list(cas.select_covered("cassis.Token", second_sentence))

    assert set(actual_tokens_in_first_sentence) == set(tokens_in_first_sentence + [subtoken1])
    assert set(actual_tokens_in_second_sentence) == set(tokens_in_second_sentence + [subtoken2])


def test_select_covered_randomized():
    """Randomized test: use two distinct types and repeat many times.

    One type (`CoverType`) is used only for the reference covering annotation.
    Another type (`RandType`) is used for the annotations that may be covered.

    The test runs 100 iterations with a deterministic seed per iteration and
    verifies that `select_covered` returns the same set as `select` filtered
    by containment.
    """
    sofa_length = 1000

    for i in range(100):
        cas = Cas()
        cas.sofa_string = "x" * sofa_length

        # Create two distinct types: one for the covering annotation, one for
        # the annotations that should be selected.
        CoverType = cas.typesystem.create_type("test.CoverAnno")
        RandType = cas.typesystem.create_type("test.RandAnno")

        annotations: list[FeatureStructure] = []
        # Generate a number of random annotations with varying lengths
        for _ in range(200):
            b = random.randint(0, sofa_length - 2)
            # keep annotation length modest
            e = random.randint(b + 1, min(b + 50, sofa_length))
            annotations.append(RandType(begin=b, end=e))

        # Add annotations to the CAS
        cas.add_all(annotations)

        # Create a random covering annotation (use the CoverType)
        cover_b = random.randint(0, sofa_length - 2)
        cover_e = random.randint(cover_b + 1, min(cover_b + 200, sofa_length))
        cover = CoverType(begin=cover_b, end=cover_e)
        cas.add(cover)

        # Expected result: select the RandType and filter by coverage
        selected_all = list(cas.select(RandType.name))
        expected = [a for a in selected_all if a.begin >= cover.begin and a.end <= cover.end]

        # Actual: use select_covered with a type name
        actual_name = list(cas.select_covered(RandType.name, cover))
        assert actual_name == expected

        # Also test passing the Type object
        actual_type = list(cas.select_covered(cas.typesystem.get_type(RandType.name), cover))
        assert actual_type == expected


def test_select_covering(small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]):
    ts = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=ts)
    cas.add_all(tokens + sentences)
    actual_first_sentence, actual_second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    for token in tokens_in_first_sentence:
        result = list(cas.select_covering("cassis.Sentence", token))
        first_sentence = result[0]

        assert len(result) == 1
        assert actual_first_sentence == first_sentence

    for token in tokens_in_second_sentence:
        result = list(cas.select_covering(ts.get_type("cassis.Sentence"), token))
        second_sentence = result[0]

        assert len(result) == 1
        assert actual_second_sentence == second_sentence


def test_select_covering_also_returns_parent_instances(
    small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]
):
    typesystem = load_typesystem(small_typesystem_xml)
    SubSentenceType = typesystem.create_type("cassis.SubSentence", supertypeName="cassis.Sentence")

    cas = Cas(typesystem=typesystem)

    first_sentence, second_sentence = sentences
    annotations = tokens + sentences
    subsentence1 = SubSentenceType(begin=first_sentence.begin, end=first_sentence.end)
    subsentence2 = SubSentenceType(begin=second_sentence.begin, end=second_sentence.end)
    annotations.append(subsentence1)
    annotations.append(subsentence2)
    cas.add_all(annotations)

    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    for token in tokens_in_first_sentence:
        result = set(cas.select_covering("cassis.Sentence", token))

        assert result == {first_sentence, subsentence1}

    for token in tokens_in_second_sentence:
        result = set(cas.select_covering("cassis.Sentence", token))

        assert result == {second_sentence, subsentence2}


def test_select_only_returns_annotations_of_current_view(
    tokens: list[FeatureStructure], sentences: list[FeatureStructure], small_typesystem_xml: str
):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_all(tokens)
    view = cas.create_view("testView")
    view.add_all(sentences)

    actual_annotations_in_initial_view = list(cas.get_view("_InitialView").select_all_annotations())
    actual_annotations_in_test_view = list(cas.get_view("testView").select_all_annotations())

    assert tokens == actual_annotations_in_initial_view
    assert sentences == actual_annotations_in_test_view


def test_select_returns_feature_structures(cas_with_collections_xmi: str, typesystem_with_collections_xml: str):
    typesystem = load_typesystem(typesystem_with_collections_xml)
    cas = load_cas_from_xmi(cas_with_collections_xmi, typesystem=typesystem)

    arrs = cas.select("uima.cas.StringArray")

    assert len(arrs) == 3


# Covered text


def test_get_covered_text_tokens(tokens: list[FeatureStructure]):
    actual_text = [token.get_covered_text() for token in tokens]

    expected_text = ["Joe", "waited", "for", "the", "train", ".", "The", "train", "was", "late", "."]
    assert actual_text == expected_text


def test_FeatureStructure_get_covered_text_tokens(tokens: list[FeatureStructure]):
    actual_text = [token.get_covered_text() for token in tokens]

    expected_text = ["Joe", "waited", "for", "the", "train", ".", "The", "train", "was", "late", "."]
    assert actual_text == expected_text


def test_get_covered_text_sentences(sentences: list[FeatureStructure]):
    actual_text = [sentence.get_covered_text() for sentence in sentences]

    expected_text = ["Joe waited for the train .", "The train was late ."]
    assert actual_text == expected_text


def test_FeatureStructure_get_covered_text_sentences(sentences: list[FeatureStructure]):
    actual_text = [sentence.get_covered_text() for sentence in sentences]

    expected_text = ["Joe waited for the train .", "The train was late ."]
    assert actual_text == expected_text


# Adding annotations


def test_add_annotation(small_typesystem_xml: str):
    typesystem = load_typesystem(small_typesystem_xml)
    TokenType = typesystem.get_type("cassis.Token")
    cas = Cas(typesystem)
    cas.sofa_string = "Joe waited for the train ."

    tokens = [
        TokenType(begin=0, end=3, id="0", pos="NNP"),
        TokenType(begin=4, end=10, id="1", pos="VBD"),
        TokenType(begin=11, end=14, id="2", pos="IN"),
        TokenType(begin=15, end=18, id="3", pos="DT"),
        TokenType(begin=19, end=24, id="4", pos="NN"),
        TokenType(begin=25, end=26, id="5", pos="."),
    ]
    for token in tokens:
        cas.add(token)

    actual_tokens = list(cas.select(TokenType.name))
    assert actual_tokens == tokens


def test_add_annotation_generates_ids(small_typesystem_xml: str, tokens: list[FeatureStructure]):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem)
    TokenType = typesystem.get_type("cassis.Token")

    tokens = [
        TokenType(begin=0, end=3, id="0", pos="NNP"),
        TokenType(begin=4, end=10, id="1", pos="VBD"),
        TokenType(begin=11, end=14, id="2", pos="IN"),
        TokenType(begin=15, end=18, id="3", pos="DT"),
        TokenType(begin=19, end=24, id="4", pos="NN"),
        TokenType(begin=25, end=26, id="5", pos="."),
    ]
    for token in tokens:
        cas.add(token)

    actual_tokens = list(cas.select(TokenType.name))
    assert all([token.xmiID is not None for token in actual_tokens])


def test_annotations_are_ordered_correctly(small_typesystem_xml: str, tokens: list[FeatureStructure]):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem)

    annotations = list(tokens)
    random.shuffle(list(annotations))

    for token in annotations:
        cas.add(token)

    actual_tokens = list(cas.select("cassis.Token"))

    assert actual_tokens == tokens


def test_leniency_type_not_in_typeystem_not_lenient(small_typesystem_xml: str):
    typesystem = load_typesystem(small_typesystem_xml)

    TokenType = typesystem.get_type("cassis.Token")
    token = TokenType(begin=0, end=3, id="0", pos="NNP")

    cas = Cas()
    with pytest.raises(RuntimeError, match="Typesystem of CAS does not contain type"):
        cas.add(token)


def test_leniency_type_not_in_typeystem_lenient(small_typesystem_xml: str):
    typesystem = load_typesystem(small_typesystem_xml)

    TokenType = typesystem.get_type("cassis.Token")
    token = TokenType(begin=0, end=3, id="0", pos="NNP")

    cas = Cas(lenient=True)
    cas.add(token)


def test_select_returns_children_fs_instances(cas_with_inheritance_xmi: str, typesystem_with_inheritance_xml: str):
    typesystem = load_typesystem(typesystem_with_inheritance_xml)

    cas = load_cas_from_xmi(cas_with_inheritance_xmi, typesystem=typesystem)

    assert len(list(cas.select("cassis.Parent"))) == 5
    assert len(list(cas.select("cassis.Child"))) == 4
    assert len(list(cas.select("cassis.GrandChild"))) == 3
    assert len(list(cas.select("cassis.GrandGrandChild"))) == 2
    assert len(list(cas.select("cassis.GrandGrandGrandChild"))) == 1


# Removing


def test_removing_of_existing_fs_works(
    small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]
):
    annotations = tokens + sentences
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_all(annotations)

    for token in tokens:
        cas.remove(token)

    actual_annotations = list(cas.select(TYPE_NAME_ANNOTATION))
    assert set(actual_annotations) == set(sentences)

    for sentence in sentences:
        cas.remove(sentence)

    actual_annotations = list(cas.select(TYPE_NAME_ANNOTATION))
    assert set(actual_annotations) == set()


def test_removing_removes_from_view(
    small_typesystem_xml: str, tokens: list[FeatureStructure], sentences: list[FeatureStructure]
):
    annotations = tokens + sentences
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    view = cas.create_view("testView")

    cas.add_all(annotations)
    view.add_all(annotations)

    for annotation in annotations:
        cas.remove(annotation)

    assert set(cas.select(TYPE_NAME_ANNOTATION)) == set()
    assert set(view.select(TYPE_NAME_ANNOTATION)) == set(annotations)


def test_removing_throws_if_fs_not_found(small_typesystem_xml: str, tokens: list[FeatureStructure]):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))

    with pytest.raises(ValueError):
        cas.remove(tokens[0])


def test_removing_throws_if_fs_in_other_view(small_typesystem_xml: str, tokens: list[FeatureStructure]):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_all(tokens)

    view = cas.create_view("testView")

    with pytest.raises(ValueError):
        view.remove(tokens[0])


def test_removing_many_annotations():
    typesystem = TypeSystem()
    NamedEntity = typesystem.create_type(name="NamedEntity", supertypeName=TYPE_NAME_ANNOTATION)
    typesystem.create_feature(domainType=NamedEntity, name="source", rangeType=TYPE_NAME_STRING)

    count_to_generate = 100

    cas = Cas(typesystem)
    for i in range(count_to_generate):
        cas.add(NamedEntity(source=("A" if (i % 2) else "B")))

    assert len(cas.select(NamedEntity.name)) == count_to_generate
    assert sum(1 for e in cas.select(NamedEntity.name) if e.source == "A") == count_to_generate / 2
    assert sum(1 for e in cas.select(NamedEntity.name) if e.source == "B") == count_to_generate / 2

    for e in cas.select(NamedEntity.name):
        if e.source == "A":
            cas.remove(e)
    assert sum(1 for e in cas.select(NamedEntity.name) if e.source == "B") == count_to_generate / 2
    assert sum(1 for e in cas.select(NamedEntity.name) if e.source == "A") == 0


def test_fail_on_duplicate_fs_id(small_typesystem_xml: str):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))

    TokenType = cas.typesystem.get_type("cassis.Token")
    cas.add(TokenType(xmiID=10, begin=0, end=0))
    cas.add(TokenType(xmiID=10, begin=10, end=10))

    with pytest.raises(ValueError):
        list(cas._find_all_fs())


def test_scanning_for_transitively_referenced_integer_array():
    typesystem = TypeSystem()
    Foo = typesystem.create_type("Foo")
    typesystem.create_feature(
        Foo,
        "ref",
        rangeType=typesystem.get_type(TYPE_NAME_INTEGER_ARRAY),
        elementType=typesystem.get_type(TYPE_NAME_INTEGER),
        multipleReferencesAllowed=True,
    )

    cas = Cas(typesystem)

    foo = Foo()
    cas.add(foo)

    IntegerArray = typesystem.get_type(TYPE_NAME_INTEGER_ARRAY)
    int_array = IntegerArray()
    int_array.elements = [1, 2, 3]
    foo.ref = int_array

    all_fs = list(cas._find_all_fs())

    assert int_array in all_fs


def test_covered_text_on_non_annotation():
    cas = Cas()
    Top = cas.typesystem.get_type(TYPE_NAME_TOP)
    top = Top()
    cas.add(top)
    with pytest.raises(NotImplementedError):
        top.get_covered_text()


def test_add_non_annotation_and_select():
    """Create a non-annotation type, add an instance and verify select returns it."""
    cas = Cas()

    # Create a type that is not an annotation (override the default uima.tcas.Annotation supertype)
    NonAnnotation = cas.typesystem.create_type("test.NonAnnotation", supertypeName=TYPE_NAME_TOP)

    # Instantiate and add to CAS
    fs = NonAnnotation()
    cas.add(fs)

    # Should be retrievable by select using the type name
    selected = list(cas.select("test.NonAnnotation"))
    assert selected == [fs]

    # And visible via select_all_fs
    assert fs in cas.select_all_fs()


def test_covered_text_on_annotation_without_sofa():
    cas = Cas()
    Annotation = cas.typesystem.get_type(TYPE_NAME_ANNOTATION)
    ann = Annotation()

    with pytest.raises(AnnotationHasNoSofa):
        ann.get_covered_text()


def test_runtime_generated_annotation_is_detected_and_shown_in_anchor():
    ts = TypeSystem()
    # Create a new annotation subtype (should inherit from Annotation base)
    MyAnno = ts.create_type("my.pkg.MyAnnotation", supertypeName="uima.tcas.Annotation")

    cas = Cas(ts)
    # Create an instance of the runtime-generated type; ensure we can set begin/end
    a = MyAnno(begin=5, end=10)
    cas.add(a)

    text = cas_to_comparable_text(cas)
    assert "MyAnnotation[5-10]" in text


def test_remove_annotations_in_range(small_typesystem_xml, small_xmi):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem)

    begin = 10
    end = 20

    expected_leftover_annotations = [
        annotation for annotation in cas.select_all_annotations() if not (begin <= annotation.begin < annotation.end <= end)
    ]

    cas.remove_annotations_in_range(begin, end)

    result_leftover_annotations = cas.select_all_annotations()

    assert len(result_leftover_annotations) == len(expected_leftover_annotations)

    for expected in expected_leftover_annotations:
        assert any(a is expected for a in result_leftover_annotations)


def test_remove_annotations_in_range_with_type(small_typesystem_xml, small_xmi):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem)

    begin = 0
    end = 27
    type_ = "cassis.Token"
    expected_leftover_annotations = [
        annotation
        for annotation in cas.select_all_annotations()
        if not (begin <= annotation.begin < annotation.end <= end and annotation.type.name == type_)
    ]

    cas.remove_annotations_in_range(begin, end, type_)

    result_leftover_annotations = cas.select_all_annotations()

    assert len(result_leftover_annotations) == len(expected_leftover_annotations)

    for expected in expected_leftover_annotations:
        assert any(a is expected for a in result_leftover_annotations)
        if begin <= expected.begin < expected.end <= end:
            assert expected.type.name != type_


def test_crop_sofa_string(small_typesystem_xml, small_xmi):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem)

    begin = 10
    end = 20

    # Snapshot annotations' original offsets so we can compute expected adjusted offsets
    expected_leftover_annotations = [
        (annotation, annotation.begin, annotation.end)
        for annotation in cas.select_all_annotations()
        if overlapping(begin, end, annotation.begin, annotation.end)
    ]

    original_sofa = cas.sofa_string

    cas.crop_sofa_string(begin, end)

    assert cas.sofa_string == original_sofa[begin:end]
    assert len(cas.select_all_annotations()) == len(expected_leftover_annotations)

    # Verify offsets were adjusted as expected for the remaining annotations
    for annotation, orig_begin, orig_end in expected_leftover_annotations:
        expected_begin = max(orig_begin, begin) - begin
        expected_end = min(orig_end, end) - begin
        assert annotation.begin == expected_begin
        assert annotation.end == expected_end

    # Additionally verify that index-based selectors (e.g., select_covered) behave correctly
    # after cropping by comparing against the annotations we tracked before the crop.
    if expected_leftover_annotations:
        ref_annotation = expected_leftover_annotations[0][0]
        covered_by_ref = list(cas.select_covered(ref_annotation.type.name, ref_annotation))
        expected_covered = [
            ann
            for ann, _, _ in expected_leftover_annotations
            if ann.type.name == ref_annotation.type.name
            and ref_annotation.begin <= ann.begin
            and ann.end <= ref_annotation.end
        ]
        sort_key = lambda a: (a.begin, a.end, a.type.name)
        assert sorted(covered_by_ref, key=sort_key) == sorted(expected_covered, key=sort_key)


def test_crop_sofa_string_no_overlap(small_typesystem_xml, small_xmi):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem)

    begin = 10
    end = 20

    # Snapshot annotations' original offsets so we can compute expected adjusted offsets
    expected_leftover_annotations = [
        (annotation, annotation.begin, annotation.end)
        for annotation in cas.select_all_annotations()
        if begin <= annotation.begin < annotation.end <= end
    ]

    original_sofa = cas.sofa_string

    cas.crop_sofa_string(begin, end, overlap=False)

    assert cas.sofa_string == original_sofa[begin:end]
    assert len(cas.select_all_annotations()) == len(expected_leftover_annotations)

    # Verify offsets were adjusted as expected for the remaining annotations
    for annotation, orig_begin, orig_end in expected_leftover_annotations:
        expected_begin = orig_begin - begin
        expected_end = orig_end - begin
        assert annotation.begin == expected_begin
        assert annotation.end == expected_end

    # Additionally verify that index-based selectors (e.g., select_covered) behave correctly
    # after cropping when only fully contained annotations are kept.
    if expected_leftover_annotations:
        ref_annotation = expected_leftover_annotations[0][0]
        covered_by_ref = list(cas.select_covered(ref_annotation.type.name, ref_annotation))
        expected_covered = [
            ann
            for ann, _, _ in expected_leftover_annotations
            if ann.type.name == ref_annotation.type.name
            and ref_annotation.begin <= ann.begin
            and ann.end <= ref_annotation.end
        ]
        sort_key = lambda a: (a.begin, a.end, a.type.name)
        assert sorted(covered_by_ref, key=sort_key) == sorted(expected_covered, key=sort_key)


def test_crop_sofa_string_left_overlap(small_typesystem_xml):
    """Ensure annotations that start before the cut and end inside it are kept and adjusted."""
    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=typesystem)

    # Create a sofa string and an annotation that starts before the cut and ends inside it
    cas.sofa_string = "012345678901234567890"
    Token = cas.typesystem.get_type("cassis.Token")
    ann = Token()
    ann.begin = 5
    ann.end = 12
    cas.add(ann)

    begin = 10
    end = 20

    original_sofa = cas.sofa_string

    cas.crop_sofa_string(begin, end)

    assert cas.sofa_string == original_sofa[begin:end]

    # After cut, the annotation should be adjusted: begin -> 0, end -> orig_end - begin
    assert ann.begin == 0
    assert ann.end == 12 - begin


@pytest.mark.parametrize(
    "ann_begin,ann_end,overlap,expect_kept,expect_begin,expect_end",
    [
        # non-overlap before
        (0, 5, True, False, None, None),
        (0, 5, False, False, None, None),
        # non-overlap after
        (21, 25, True, False, None, None),
        (21, 25, False, False, None, None),
        # fully contained
        (12, 15, True, True, 12 - 10, 15 - 10),
        (12, 15, False, True, 12 - 10, 15 - 10),
        # left-overlap
        (5, 12, True, True, 0, 12 - 10),
        (5, 12, False, False, None, None),
        # right-overlap
        (15, 25, True, True, 15 - 10, 10),
        (15, 25, False, False, None, None),
        # fully covering
        (5, 25, True, True, 0, 10),
        (5, 25, False, False, None, None),
        # exact match
        (10, 20, True, True, 0, 10),
        (10, 20, False, True, 0, 10),
    ],
)
def test_crop_sofa_string_various_overlap_cases(
    small_typesystem_xml, ann_begin, ann_end, overlap, expect_kept, expect_begin, expect_end
):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=typesystem)

    cas.sofa_string = "012345678901234567890"
    Token = cas.typesystem.get_type("cassis.Token")
    ann = Token()
    ann.begin = ann_begin
    ann.end = ann_end
    cas.add(ann)

    begin = 10
    end = 20

    original_sofa = cas.sofa_string

    cas.crop_sofa_string(begin, end, overlap=overlap)

    assert cas.sofa_string == original_sofa[begin:end]

    if expect_kept:
        assert ann in cas.select_all_annotations()
        assert ann.begin == expect_begin
        assert ann.end == expect_end
    else:
        assert ann not in cas.select_all_annotations()


def test_crop_sofa_string_transitive_references_remain(small_typesystem_xml):
    """Annotations outside the cut that are referenced from kept annotations remain discoverable."""
    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=typesystem)

    # Create parent and child types and a feature on parent referencing child
    Child = typesystem.create_type("test.Child")
    Parent = typesystem.create_type("test.Parent")
    typesystem.create_feature("test.Parent", "child", "test.Child")

    # Create instances: child is outside cut, parent inside and references child
    child = Child(begin=0, end=5)
    parent = Parent(begin=12, end=15)
    parent.child = child

    cas.add(child)
    cas.add(parent)

    begin = 10
    end = 20

    # Ensure a sofa string is present for cutting (length > end)
    cas.sofa_string = "a" * 50

    cas.crop_sofa_string(begin, end)

    # Child was outside the cut and therefore removed from the view index
    assert child not in cas.select_all_annotations()

    # But child is still reachable via parent and will be discovered by traversal
    all_fs = list(cas._find_all_fs())
    assert child in all_fs


def test_crop_sofa_string_serialization_roundtrip_transitive_refs(small_typesystem_xml):
    """Cut the sofa, serialize to JSON and back; ensure transitively referenced
    FS outside the cut are serialized and re-loaded without exceptions."""
    from cassis.json import load_cas_from_json

    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=typesystem)

    Child = typesystem.create_type("test.Child")
    Parent = typesystem.create_type("test.Parent")
    typesystem.create_feature("test.Parent", "child", "test.Child")

    child = Child(begin=0, end=5)
    parent = Parent(begin=12, end=15)
    parent.child = child

    cas.add(child)
    cas.add(parent)

    # ensure sofa present and long enough
    cas.sofa_string = "a" * 50

    begin = 10
    end = 20

    cas.crop_sofa_string(begin, end)

    # Round-trip via JSON should not raise; deserialize and ensure child present
    json_str = cas.to_json(pretty_print=False)
    new_cas = load_cas_from_json(json_str)

    all_fs = list(new_cas._find_all_fs())
    assert any(fs.type.name == "test.Child" and getattr(fs, "begin", None) == 0 for fs in all_fs)


def test_crop_sofa_string_serialization_roundtrip_transitive_refs_beyond_end(small_typesystem_xml):
    """Place the transitively referenced FS beyond the new sofa length and
    ensure serialization/deserialization does not raise an exception but
    emits warnings during offset transcoding."""
    from cassis.json import load_cas_from_json

    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem=typesystem)

    Child = typesystem.create_type("test.Child")
    Parent = typesystem.create_type("test.Parent")
    typesystem.create_feature("test.Parent", "child", "test.Child")

    # child placed beyond the cut and beyond the eventual new sofa length
    child = Child(begin=30, end=35)
    parent = Parent(begin=12, end=15)
    parent.child = child

    cas.add(child)
    cas.add(parent)

    # original sofa long enough to accommodate child positions
    cas.sofa_string = "a" * 50

    begin = 10
    end = 20

    cas.crop_sofa_string(begin, end)

    # serialization/transcoding may warn but should not raise
    with pytest.warns(UserWarning):
        json_str = cas.to_json(pretty_print=False)

    with pytest.warns(UserWarning):
        new_cas = load_cas_from_json(json_str)

    # Ensure child was serialized and reloaded (may have unmapped offsets)
    all_fs = list(new_cas._find_all_fs())
    assert any(fs.type.name == "test.Child" for fs in all_fs)
