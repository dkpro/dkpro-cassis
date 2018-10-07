import pytest

from tests.fixtures import *

from lxml_asserts import assert_xml_equal

from cassis import load_typesystem, TypeSystem


# Feature

def test_feature_can_be_added():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name='test.Type')
    typesystem.add_feature(type_=test_type, name='testFeature', rangeTypeName='String', description='A test feature')

    actual_type = typesystem.get_type('test.Type')
    actual_feature = actual_type.get_feature('testFeature')
    assert actual_feature.name == 'testFeature'
    assert actual_feature.rangeTypeName == 'String'
    assert actual_feature.description == 'A test feature'


def test_feature_adding_throws_if_already_existing():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name='test.Type')
    typesystem.add_feature(type_=test_type, name='testFeature', rangeTypeName='String', description='A test feature')

    with pytest.raises(ValueError):
        typesystem.add_feature(type_=test_type, name='testFeature', rangeTypeName='String',
                               description='A test feature')

# Type


def test_type_can_be_created():
    typesystem = TypeSystem()

    test_type = typesystem.create_type(name='test.Type')

    assert test_type.name == 'test.Type'
    assert test_type.supertypeName == 'uima.cas.AnnotationBase'


def test_type_can_create_instances():
    typesystem = TypeSystem()
    test_type = typesystem.create_type(name='test.Type')
    typesystem.add_feature(type_=test_type, name='testFeature', rangeTypeName='String', description='A test feature')

    annotation = test_type(begin=0, end=42, testFeature='testValue')

    assert annotation.begin == 0
    assert annotation.end == 42
    assert annotation.testFeature == 'testValue'


def test_type_can_create_instance_with_inherited_fields():
    typesystem = TypeSystem()

    parent_type = typesystem.create_type(name='test.ParentType')
    typesystem.add_feature(type_=parent_type, name='parentFeature', rangeTypeName='String')

    child_type = typesystem.create_type(name='test.ChildType', supertypeName=parent_type.name)
    typesystem.add_feature(type_=child_type, name='childFeature', rangeTypeName='Integer')

    annotation = child_type(parentFeature='parent', childFeature='child')

    assert annotation.parent_feature == 'parent'
    assert annotation.child_feature == 'child'


# Deserializing

def test_deserializing_from_file(small_typesystem_path):
    with open(small_typesystem_path, 'rb') as f:
        load_typesystem(f)


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
    load_typesystem(cas_xmi)


def test_deserializing_small_typesystem(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    assert len(list(typesystem.get_types())) == 3

    # Assert annotation type
    annotation_type = typesystem.get_type('uima.tcas.DocumentAnnotation')
    assert annotation_type.name == 'uima.tcas.DocumentAnnotation'
    assert annotation_type.supertypeName == 'uima.tcas.Annotation'

    language_feature = annotation_type.get_feature('language')
    assert language_feature.name == 'language'
    assert language_feature.rangeTypeName == 'uima.cas.String'

    # Assert token type
    token_type = typesystem.get_type('cassis.Token')
    assert token_type.name == 'cassis.Token'
    assert token_type.supertypeName == 'uima.tcas.Annotation'

    token_id_feature = token_type.get_feature('id')
    assert token_id_feature.name == 'id'
    assert token_id_feature.rangeTypeName == 'uima.cas.Integer'

    token_pos_feature = token_type.get_feature('pos')
    assert token_pos_feature.name == 'pos'
    assert token_pos_feature.rangeTypeName == 'uima.cas.String'

    # Assert sentence type
    sentence_type = typesystem.get_type('cassis.Sentence')
    assert sentence_type.name == 'cassis.Sentence'
    assert sentence_type.supertypeName == 'uima.tcas.Annotation'

    sentence_type_id_feature = sentence_type.get_feature('id')
    assert sentence_type_id_feature.name == 'id'
    assert sentence_type_id_feature.rangeTypeName == 'uima.cas.Integer'


# Serializing

def test_serializing_small_typesystem_to_string(small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)

    actual_xml = typesystem.to_xml()

    assert_xml_equal(actual_xml, small_typesystem_xml.encode('utf-8'))


def test_serializing_small_typesystem_to_file_path(tmpdir, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    path = tmpdir.join('typesystem.xml')

    typesystem.to_xml(path)

    with open(path, 'rb') as actual:
        assert_xml_equal(actual.read(), small_typesystem_xml.encode('utf-8'))


def test_serializing_small_typesystem_to_file(tmpdir, small_typesystem_xml):
    typesystem = load_typesystem(small_typesystem_xml)
    path = tmpdir.join('typesystem.xml')

    with open(path, 'wb') as f:
        typesystem.to_xml(f)

    with open(path, 'rb') as actual:
        assert_xml_equal(actual.read(), small_typesystem_xml.encode('utf-8'))
