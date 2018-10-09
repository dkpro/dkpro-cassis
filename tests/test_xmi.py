from tests.fixtures import *

from lxml_asserts import assert_xml_equal

from cassis import *


# Deserializing

def test_deserializing_from_file(small_xmi_path, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    with open(small_xmi_path, 'rb') as f:
        load_cas_from_xmi(f, typesystem=typesystem)


def test_deserializing_from_string(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas_xmi = '''<?xml version="1.0" encoding="UTF-8"?>
    <xmi:XMI xmlns:tcas="http:///uima/tcas.ecore" xmlns:xmi="http://www.omg.org/XMI" xmlns:cas="http:///uima/cas.ecore"
             xmlns:cassis="http:///cassis.ecore" xmi:version="2.0">
        <cas:NULL xmi:id="0"/>
        <tcas:DocumentAnnotation xmi:id="8" sofa="1" begin="0" end="47" language="x-unspecified"/>
        <cassis:Sentence xmi:id="79" sofa="1" begin="0" end="26" id="0"/>
        <cassis:Sentence xmi:id="84" sofa="1" begin="27" end="47" id="1"/>
        <cas:Sofa xmi:id="1" sofaNum="1" sofaID="mySofa" mimeType="text/plain"
                  sofaString="Joe waited for the train . The train was late ."/>
        <cas:View sofa="1" members="8 13 19 25 31 37 43 49 55 61 67 73 79 84"/>
    </xmi:XMI>    
    '''
    load_cas_from_xmi(cas_xmi, typesystem=typesystem)

def test_namespaces_are_parsed(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    cas = load_cas_from_xmi(small_xmi, typesystem=typesystem)

    expected_namespaces = {
        'xmi': 'http://www.omg.org/XMI',
        'cas': 'http:///uima/cas.ecore',
        'cassis': 'http:///cassis.ecore',
        'tcas': 'http:///uima/tcas.ecore'

    }
    assert cas.namespaces == expected_namespaces


def test_sofas_are_parsed(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem)

    expected_sofas = [Sofa(xmiID=1, sofaNum=1, sofaID='mySofa', mimeType='text/plain',
                           sofaString='Joe waited for the train . The train was late .')]
    assert cas.sofas == expected_sofas


def test_views_are_parsed(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem=typesystem)

    expected_views = [View(sofa=1, members=[8, 13, 19, 25, 31, 37, 43, 49, 55, 61, 67, 73, 79, 84])]
    assert cas.views == expected_views


def test_simple_features_are_parsed(small_xmi, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    cas = load_cas_from_xmi(small_xmi, typesystem=typesystem)

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


# Serializing

@pytest.mark.parametrize('xmi, typesystem_xml', [
    (pytest.lazy_fixture('small_xmi'), pytest.lazy_fixture('small_typesystem_xml')),
    (pytest.lazy_fixture('cas_with_inheritance_xmi'), pytest.lazy_fixture('typesystem_with_inheritance_xml')),
])
def test_serializing_cas_to_string(xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)

    actual_xml = cas.to_xmi()

    assert_xml_equal(actual_xml, xmi.encode('utf-8'))


@pytest.mark.parametrize('xmi, typesystem_xml', [
    (pytest.lazy_fixture('small_xmi'), pytest.lazy_fixture('small_typesystem_xml')),
    (pytest.lazy_fixture('cas_with_inheritance_xmi'), pytest.lazy_fixture('typesystem_with_inheritance_xml')),
])
def test_serializing_cas_to_file_path(tmpdir, xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)
    path = tmpdir.join('cas.xml')

    cas.to_xmi(path)

    with open(path, 'rb') as actual:
        assert_xml_equal(actual.read(), xmi.encode('utf-8'))


@pytest.mark.parametrize('xmi, typesystem_xml', [
    (pytest.lazy_fixture('small_xmi'), pytest.lazy_fixture('small_typesystem_xml')),
    (pytest.lazy_fixture('cas_with_inheritance_xmi'), pytest.lazy_fixture('typesystem_with_inheritance_xml')),
])
def test_serializing_cas_to_file(tmpdir, xmi, typesystem_xml):
    typesystem = load_typesystem(typesystem_xml)
    cas = load_cas_from_xmi(xmi, typesystem=typesystem)
    path = tmpdir.join('cas.xml')

    with open(path, 'wb') as f:
        cas.to_xmi(f)

    with open(path, 'rb') as actual:
        assert_xml_equal(actual.read(), xmi.encode('utf-8'))
