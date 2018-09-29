import random

from tests.fixtures import *

from cassis.cas import Cas, Sofa, View
import cassis.typesystem


def test_select(tokens, sentences):
    annotations = tokens + sentences
    cas = Cas(annotations=annotations)

    actual_tokens = list(cas.select('cassis.Token'))
    actual_sentences = list(cas.select('cassis.Sentence'))

    assert actual_tokens == tokens
    assert actual_sentences == sentences


def test_select_covered(tokens, sentences):
    annotations = tokens + sentences
    cas = Cas(annotations=annotations)
    first_sentence, second_sentence = sentences
    tokens_in_first_sentence = tokens[:6]
    tokens_in_second_sentence = tokens[6:]

    actual_tokens_in_first_sentence = list(cas.select_covered('cassis.Token', first_sentence))
    actual_tokens_in_second_sentence = list(cas.select_covered('cassis.Token', second_sentence))

    assert actual_tokens_in_first_sentence == tokens_in_first_sentence
    assert actual_tokens_in_second_sentence == tokens_in_second_sentence


def test_get_covered_text_tokens(tokens):
    sofa = Sofa(sofaNum=1, sofaString='Joe waited for the train . The train was late .')
    cas = Cas(annotations=tokens, sofas=[sofa])

    actual_text = [cas.get_covered_text(token) for token in tokens]

    expected_text = [
        'Joe', 'waited', 'for', 'the', 'train', '.',
        'The', 'train', 'was', 'late', '.'
    ]
    assert actual_text == expected_text


def test_get_covered_text_sentences(sentences):
    sofa = Sofa(sofaNum=1, sofaString='Joe waited for the train . The train was late .')
    cas = Cas(annotations=sentences, sofas=[sofa])

    actual_text = [cas.get_covered_text(sentence) for sentence in sentences]

    expected_text = [
        'Joe waited for the train .',
        'The train was late .'
    ]
    assert actual_text == expected_text


def test_add_annotation(small_typesystem_xml):
    sofa = Sofa(sofaNum=1, sofaString='Joe waited for the train .')
    cas = Cas(sofas=[sofa])
    typesystem = load_typesystem(small_typesystem_xml)
    TokenType = typesystem.get_type('cassis.Token')

    tokens = [
        TokenType(xmiID=13, sofa=1, begin=0, end=3, id='0', pos='NNP'),
        TokenType(xmiID=19, sofa=1, begin=4, end=10, id='1', pos='VBD'),
        TokenType(xmiID=25, sofa=1, begin=11, end=14, id='2', pos='IN'),
        TokenType(xmiID=31, sofa=1, begin=15, end=18, id='3', pos='DT'),
        TokenType(xmiID=37, sofa=1, begin=19, end=24, id='4', pos='NN'),
        TokenType(xmiID=43, sofa=1, begin=25, end=26, id='5', pos='.'),
    ]
    for token in tokens:
        cas.add_annotation(token)

    actual_tokens = list(cas.select(TokenType.name))
    assert actual_tokens == tokens


def test_add_annotation_generates_ids(small_typesystem_xml, tokens):
    cas = Cas()
    typesystem = load_typesystem(small_typesystem_xml)
    TokenType = typesystem.get_type('cassis.Token')

    tokens = [
        TokenType(sofa=1, begin=0, end=3, id='0', pos='NNP'),
        TokenType(sofa=1, begin=4, end=10, id='1', pos='VBD'),
        TokenType(sofa=1, begin=11, end=14, id='2', pos='IN'),
        TokenType(sofa=1, begin=15, end=18, id='3', pos='DT'),
        TokenType(sofa=1, begin=19, end=24, id='4', pos='NN'),
        TokenType(sofa=1, begin=25, end=26, id='5', pos='.'),
    ]
    for token in tokens:
        cas.add_annotation(token)

    actual_tokens = list(cas.select(TokenType.name))
    assert all([token.xmiID != None for token in actual_tokens])


def test_annotations_are_ordered_correctly(tokens):
    annotations = list(tokens)
    random.shuffle(list(annotations))
    cas = Cas()
    for token in annotations:
        cas.add_annotation(token)

    actual_tokens = list(cas.select('cassis.Token'))

    assert actual_tokens == tokens
