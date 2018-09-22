from tests.fixtures import small_typesystem

from cassis.typesystem import TypeSystem, Type, Feature


# Type

def test_type_can_create_instances():
    features = [Feature(name='testFeature', description='Just a test feature', rangeTypeName='String')]
    TestType = Type(name='test.Type', description='Just a test type', supertypeName='TOP', features=features)

    annotation = TestType(testFeature='testValue')

    assert annotation.testFeature == 'testValue'
