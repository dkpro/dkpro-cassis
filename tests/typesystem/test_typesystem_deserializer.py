from tests.fixtures import small_typesystem

from cassis.typesystem import Feature, Type, load_from_file, load_from_string


def test_deserializing_from_file(small_typesystem):
    load_from_file(small_typesystem)


def test_deserializing_from_string():
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
    load_from_string(cas_xmi)

def test_deserializing_small_typesystem(small_typesystem):
    typesystem = load_from_file(small_typesystem)

    assert len(typesystem) == 3

    # Assert annotation type
    annotation_features = [Feature('language', '', 'uima.cas.String')]
    annotation_type = Type('uima.tcas.DocumentAnnotation', '', 'uima.tcas.Annotation', annotation_features)
    assert typesystem.get_type('uima.tcas.DocumentAnnotation') == annotation_type

    # Assert token type
    token_features = [Feature('id', '', 'uima.cas.Integer'), Feature('pos', '', 'uima.cas.String')]
    token_type = Type('cassis.Token', '', 'uima.tcas.Annotation', token_features)
    assert typesystem.get_type('cassis.Token') == token_type

    # Assert sentence type
    sentence_features = [Feature('id', '', 'uima.cas.Integer')]
    sentence_type = Type('cassis.Sentence', '', 'uima.tcas.Annotation', sentence_features)
    assert typesystem.get_type('cassis.Sentence') == sentence_type
