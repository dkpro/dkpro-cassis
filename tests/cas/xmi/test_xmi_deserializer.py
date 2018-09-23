from tests.fixtures import small_xmi, small_typesystem

from cassis.cas import Cas, Sofa, View
from cassis.cas.xmi import load_from_file
import cassis.typesystem

def test_deserializing_smoke_test(small_xmi):
    load_from_file(small_xmi)


def test_namespaces_are_parsed(small_xmi):
    cas = load_from_file(small_xmi)

    expected_namespaces = {
        'xmi': 'http://www.omg.org/XMI',
        'cas': 'http:///uima/cas.ecore',
        'cassis': 'http:///cassis.ecore',
        'tcas': 'http:///uima/tcas.ecore'

    }
    assert cas.namespaces == expected_namespaces


def test_sofas_are_parsed(small_xmi):
    cas = load_from_file(small_xmi)

    expected_sofas = [Sofa(xmiID=1, sofaNum=1, sofaID='mySofa', mimeType='text/plain',
                           sofaString='Joe waited for the train . The train was late .')]
    assert cas.sofas == expected_sofas


def test_views_are_parsed(small_xmi):
    cas = load_from_file(small_xmi)

    expected_views = [View(sofa=1, members=[8, 13, 19, 25, 31, 37, 43, 49, 55, 61, 67, 73, 79, 84])]
    assert cas.views == expected_views


def test_simple_features_are_parsed(small_xmi, small_typesystem):
    typesystem = cassis.typesystem.load_from_file(small_typesystem)
    cas = load_from_file(small_xmi, typesystem=typesystem)

    TokenType = typesystem.get_type('cassis.Token')
    SentenceType = typesystem.get_type('cassis.Sentence')
    expected_tokens = [
        TokenType(xmiID=13, sofa=1, begin=0, end=3, id='0', pos='NNP'),
        TokenType(xmiID=19, sofa=1, begin=4, end=10, id='1', pos='VBD'),
        TokenType(xmiID=25, sofa=1, begin=11, end=14, id='2', pos='IN'),
        TokenType(xmiID=31, sofa=1, begin=15, end=18, id='3', pos='DT'),
        TokenType(xmiID=37, sofa=1, begin=19, end=24, id='4', pos='NN'),
        TokenType(xmiID=43, sofa=1, begin=25, end=26, id='5', pos='.'),
        TokenType(xmiID=49, sofa=1, begin=27, end=30, id='6', pos='DT'),
        TokenType(xmiID=55, sofa=1, begin=31, end=36, id='7', pos='NN'),
        TokenType(xmiID=61, sofa=1, begin=37, end=40, id='8', pos='VBD'),
        TokenType(xmiID=67, sofa=1, begin=41, end=45, id='9', pos='JJ'),
        TokenType(xmiID=73, sofa=1, begin=46, end=47, id='10', pos='.')
    ]
    expected_sentences = [
        SentenceType(xmiID=79, sofa=1, begin=0, end=26, id='0'),
        SentenceType(xmiID=84, sofa=1, begin=27, end=47, id='1')
    ]
    assert list(cas.select(TokenType.name)) == expected_tokens
    assert list(cas.select(SentenceType.name)) == expected_sentences
