from tests.fixtures import small_xmi

from cassis.cas import Cas, Sofa, View
from cassis.cas.xmi import XmiCasDeserializer


def test_deserializing_smoke_test(small_xmi):
    deserializer = XmiCasDeserializer()

    deserializer.parse(small_xmi)


def test_namespaces_are_parsed(small_xmi):
    deserializer = XmiCasDeserializer()

    cas = deserializer.parse(small_xmi)

    expected_namespaces = {
        'xmi': 'http://www.omg.org/XMI',
        'cas': 'http:///uima/cas.ecore',
        'cassis': 'http:///cassis.ecore',
        'tcas': 'http:///uima/tcas.ecore'

    }
    assert cas.namespaces == expected_namespaces


def test_sofas_are_parsed(small_xmi):
    deserializer = XmiCasDeserializer()

    cas = deserializer.parse(small_xmi)

    expected_sofas = [Sofa(id='1', sofaNum='1', sofaID='mySofa', mimeType='text/plain',
                           sofaString='Joe waited for the train . The train was late .')]
    assert cas.sofas == expected_sofas


def test_views_are_parsed(small_xmi):
    deserializer = XmiCasDeserializer()

    cas = deserializer.parse(small_xmi)

    expected_views = [View(sofa='1', members=[8, 13, 19, 25, 31, 37, 43, 49, 55, 61, 67, 73, 79, 84])]
    assert cas.views == expected_views
