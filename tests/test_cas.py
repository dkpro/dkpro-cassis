import random

import attr
import pytest

from cassis.cas import Cas
from tests.fixtures import *

# Cas


def test_default_typesystem_is_not_shared():
    # https://github.com/dkpro/dkpro-cassis/issues/67
    cas1 = Cas()
    cas2 = Cas()

    t1 = cas1.typesystem.create_type(name="test.Type")
    t2 = cas2.typesystem.create_type(name="test.Type")


def test_default_typesystem_is_not_shared_load_from_xmi(empty_cas_xmi):
    # https://github.com/dkpro/dkpro-cassis/issues/67
    cas1 = load_cas_from_xmi(empty_cas_xmi)
    cas2 = load_cas_from_xmi(empty_cas_xmi)

    t1 = cas1.typesystem.create_type(name="test.Type")
    t2 = cas2.typesystem.create_type(name="test.Type")


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


# Select


def test_select(small_typesystem_xml, tokens, sentences):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(tokens + sentences)

    actual_tokens = list(cas.select("cassis.Token"))
    actual_sentences = list(cas.select("cassis.Sentence"))

    assert actual_tokens == tokens
    assert actual_sentences == sentences


def test_select_also_returns_parent_instances(small_typesystem_xml, tokens, sentences):
    annotations = tokens + sentences
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(annotations)

    actual_annotations = list(cas.select("uima.tcas.Annotation"))

    assert set(actual_annotations) == set(annotations)


def test_select_covered(small_typesystem_xml, tokens, sentences):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(tokens + sentences)
    first_sentence, second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    actual_tokens_in_first_sentence = list(cas.select_covered("cassis.Token", first_sentence))
    actual_tokens_in_second_sentence = list(cas.select_covered("cassis.Token", second_sentence))

    assert actual_tokens_in_first_sentence == tokens_in_first_sentence
    assert actual_tokens_in_second_sentence == tokens_in_second_sentence


def test_select_covered_also_returns_parent_instances(small_typesystem_xml, tokens, sentences):
    typesystem = load_typesystem(small_typesystem_xml)
    SubTokenType = typesystem.create_type("cassis.SubToken", supertypeName="cassis.Token")

    annotations = tokens + sentences
    subtoken1 = SubTokenType(begin=tokens[2].begin, end=tokens[3].end)
    subtoken2 = SubTokenType(begin=tokens[8].begin, end=tokens[8].end)
    annotations.append(subtoken1)
    annotations.append(subtoken2)

    cas = Cas(typesystem=typesystem)
    cas.add_annotations(annotations)

    first_sentence, second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    actual_tokens_in_first_sentence = list(cas.select_covered("cassis.Token", first_sentence))
    actual_tokens_in_second_sentence = list(cas.select_covered("cassis.Token", second_sentence))

    assert set(actual_tokens_in_first_sentence) == set(tokens_in_first_sentence + [subtoken1])
    assert set(actual_tokens_in_second_sentence) == set(tokens_in_second_sentence + [subtoken2])


def test_select_covering(small_typesystem_xml, tokens, sentences):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(tokens + sentences)
    actual_first_sentence, actual_second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    for token in tokens_in_first_sentence:
        result = list(cas.select_covering("cassis.Sentence", token))
        first_sentence = result[0]

        assert len(result) == 1
        assert actual_first_sentence == first_sentence

    for token in tokens_in_second_sentence:
        result = list(cas.select_covering("cassis.Sentence", token))
        second_sentence = result[0]

        assert len(result) == 1
        assert actual_second_sentence == second_sentence


def test_select_covering_also_returns_parent_instances(small_typesystem_xml, tokens, sentences):
    typesystem = load_typesystem(small_typesystem_xml)
    SubSentenceType = typesystem.create_type("cassis.SubSentence", supertypeName="cassis.Sentence")

    cas = Cas(typesystem=typesystem)

    first_sentence, second_sentence = sentences
    annotations = tokens + sentences
    subsentence1 = SubSentenceType(begin=first_sentence.begin, end=first_sentence.end)
    subsentence2 = SubSentenceType(begin=second_sentence.begin, end=second_sentence.end)
    annotations.append(subsentence1)
    annotations.append(subsentence2)
    cas.add_annotations(annotations)

    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    for token in tokens_in_first_sentence:
        result = set(cas.select_covering("cassis.Sentence", token))

        assert result == {first_sentence, subsentence1}

    for token in tokens_in_second_sentence:
        result = set(cas.select_covering("cassis.Sentence", token))

        assert result == {second_sentence, subsentence2}


def test_select_only_returns_annotations_of_current_view(tokens, sentences, small_typesystem_xml):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(tokens)
    view = cas.create_view("testView")
    view.add_annotations(sentences)

    actual_annotations_in_initial_view = list(cas.get_view("_InitialView").select_all())
    actual_annotations_in_test_view = list(cas.get_view("testView").select_all())

    assert tokens == actual_annotations_in_initial_view
    assert sentences == actual_annotations_in_test_view


def test_select_returns_feature_structures(cas_with_collections_xmi, typesystem_with_collections_xml):
    typesystem = load_typesystem(typesystem_with_collections_xml)
    cas = load_cas_from_xmi(cas_with_collections_xmi, typesystem=typesystem)

    arrs = list(cas.select("cassis.StringArray"))

    assert len(arrs) == 1


# Get with path selector


def test_get_path_semargs(cas_with_references_xmi, webanno_typesystem_xml):
    typesystem = load_typesystem(webanno_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_references_xmi, typesystem=typesystem)

    pred = next(cas.select("de.tudarmstadt.ukp.dkpro.core.api.semantics.type.SemPred"))
    first_arg = pred.arguments[0]

    end = first_arg.get("target.end")

    assert end == 5


def test_get_path_stringlist():
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
    print(lst)

    assert lst.get("head") == "foo"
    assert lst.get("tail.head") == "bar"
    assert lst.get("tail.tail.head") == "baz"
    assert lst.get("tail.tail.tail.head") is None


# Covered text


def test_get_covered_text_tokens(tokens):
    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."

    actual_text = [token.get_covered_text() for token in tokens]

    expected_text = ["Joe", "waited", "for", "the", "train", ".", "The", "train", "was", "late", "."]
    assert actual_text == expected_text


def test_FeatureStructure_get_covered_text_tokens(tokens):
    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."

    actual_text = [token.get_covered_text() for token in tokens]

    expected_text = ["Joe", "waited", "for", "the", "train", ".", "The", "train", "was", "late", "."]
    assert actual_text == expected_text


def test_get_covered_text_sentences(sentences):
    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."

    actual_text = [sentence.get_covered_text() for sentence in sentences]

    expected_text = ["Joe waited for the train .", "The train was late ."]
    assert actual_text == expected_text


def test_FeatureStructure_get_covered_text_sentences(sentences):
    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."

    actual_text = [sentence.get_covered_text() for sentence in sentences]

    expected_text = ["Joe waited for the train .", "The train was late ."]
    assert actual_text == expected_text


# Adding annotations


def test_add_annotation(small_typesystem_xml):
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
        cas.add_annotation(token)

    actual_tokens = list(cas.select(TokenType.name))
    assert actual_tokens == tokens


def test_add_annotation_generates_ids(small_typesystem_xml, tokens):
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
        cas.add_annotation(token)

    actual_tokens = list(cas.select(TokenType.name))
    assert all([token.xmiID is not None for token in actual_tokens])


def test_annotations_are_ordered_correctly(small_typesystem_xml, tokens):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = Cas(typesystem)

    annotations = list(tokens)
    random.shuffle(list(annotations))

    for token in annotations:
        cas.add_annotation(token)

    actual_tokens = list(cas.select("cassis.Token"))

    assert actual_tokens == tokens


def test_leniency_type_not_in_typeystem_not_lenient(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    TokenType = typesystem.get_type("cassis.Token")
    token = TokenType(begin=0, end=3, id="0", pos="NNP")

    cas = Cas()
    with pytest.raises(RuntimeError, match="Typesystem of CAS does not contain type"):
        cas.add_annotation(token)


def test_leniency_type_not_in_typeystem_lenient(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    TokenType = typesystem.get_type("cassis.Token")
    token = TokenType(begin=0, end=3, id="0", pos="NNP")

    cas = Cas(lenient=True)
    cas.add_annotation(token)


def test_select_returns_children_fs_instances(cas_with_inheritance_xmi, typesystem_with_inheritance_xml):
    typesystem = load_typesystem(typesystem_with_inheritance_xml)

    cas = load_cas_from_xmi(cas_with_inheritance_xmi, typesystem=typesystem)

    assert len(list(cas.select("cassis.Parent"))) == 5
    assert len(list(cas.select("cassis.Child"))) == 4
    assert len(list(cas.select("cassis.GrandChild"))) == 3
    assert len(list(cas.select("cassis.GrandGrandChild"))) == 2
    assert len(list(cas.select("cassis.GrandGrandGrandChild"))) == 1


# Removing


def test_removing_of_existing_fs_works(small_typesystem_xml, tokens, sentences):
    annotations = tokens + sentences
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(annotations)

    for token in tokens:
        cas.remove_annotation(token)

    actual_annotations = list(cas.select("uima.tcas.Annotation"))
    assert set(actual_annotations) == set(sentences)

    for sentence in sentences:
        cas.remove_annotation(sentence)

    actual_annotations = list(cas.select("uima.tcas.Annotation"))
    assert set(actual_annotations) == set()


def test_removing_removes_from_view(small_typesystem_xml, tokens, sentences):
    annotations = tokens + sentences
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    view = cas.create_view("testView")

    cas.add_annotations(annotations)
    view.add_annotations(annotations)

    for annotation in annotations:
        cas.remove_annotation(annotation)

    assert set(cas.select("uima.tcas.Annotation")) == set()
    assert set(view.select("uima.tcas.Annotation")) == set(annotations)


def test_removing_throws_if_fs_not_found(small_typesystem_xml, tokens, sentences):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))

    with pytest.raises(ValueError):
        cas.remove_annotation(tokens[0])


def test_removing_throws_if_fs_in_other_view(small_typesystem_xml, tokens, sentences):
    cas = Cas(typesystem=load_typesystem(small_typesystem_xml))
    cas.add_annotations(tokens)

    view = cas.create_view("testView")

    with pytest.raises(ValueError):
        view.remove_annotation(tokens[0])
