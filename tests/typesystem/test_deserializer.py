from tests.fixtures import small_typesystem

from cassis.typesystem import TypeSystemDeserializer, Type, Feature

def test_deserializing_small_typesystem(small_typesystem):
    deserializer = TypeSystemDeserializer()

    typesystem = deserializer.parse(small_typesystem)

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

