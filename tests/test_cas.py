import random

import attr

from tests.fixtures import *

from cassis.cas import Cas, Sofa, View
import cassis.typesystem

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

    with pytest.raises(ValueError, message=r"A view with name [testView] already exists!"):
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

    with pytest.raises(KeyError, message=r"There is no view with name [testView] in this CAS!"):
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


# Select


def test_select(tokens, sentences):
    cas = Cas()
    cas.add_annotations(tokens + sentences)

    actual_tokens = list(cas.select("cassis.Token"))
    actual_sentences = list(cas.select("cassis.Sentence"))

    assert actual_tokens == tokens
    assert actual_sentences == sentences


def test_select_covered(tokens, sentences):
    cas = Cas()
    cas.add_annotations(tokens + sentences)
    first_sentence, second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    actual_tokens_in_first_sentence = list(cas.select_covered("cassis.Token", first_sentence))
    actual_tokens_in_second_sentence = list(cas.select_covered("cassis.Token", second_sentence))

    assert actual_tokens_in_first_sentence == tokens_in_first_sentence
    assert actual_tokens_in_second_sentence == tokens_in_second_sentence


def test_select_only_returns_annotations_of_current_view(tokens, sentences):
    cas = Cas()
    cas.add_annotations(tokens)
    view = cas.create_view("testView")
    view.add_annotations(sentences)

    actual_annotations_in_initial_view = list(cas.get_view("_InitialView").select_all())
    actual_annotations_in_test_view = list(cas.get_view("testView").select_all())

    assert tokens == actual_annotations_in_initial_view
    assert sentences == actual_annotations_in_test_view


def test_select_returns_feature_structures(cas_with_string_array_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(cas_with_string_array_xmi, typesystem=typesystem)

    arrs = list(cas.select("uima.cas.StringArray"))

    assert len(arrs) == 1


# Covered text


def test_get_covered_text_tokens(tokens):
    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."

    actual_text = [cas.get_covered_text(token) for token in tokens]

    expected_text = ["Joe", "waited", "for", "the", "train", ".", "The", "train", "was", "late", "."]
    assert actual_text == expected_text


def test_get_covered_text_sentences(sentences):
    cas = Cas()
    cas.sofa_string = "Joe waited for the train . The train was late ."

    actual_text = [cas.get_covered_text(sentence) for sentence in sentences]

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


def test_annotations_are_ordered_correctly(tokens):
    annotations = list(tokens)
    random.shuffle(list(annotations))
    cas = Cas()
    for token in annotations:
        cas.add_annotation(token)

    actual_tokens = list(cas.select("cassis.Token"))

    assert actual_tokens == tokens
