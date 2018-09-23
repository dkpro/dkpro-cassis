from io import BytesIO
from typing import IO

from lxml import etree

from cassis.typesystem.typesystem import TypeSystem, Type, Feature


def save_to_file(typesystem: TypeSystem, path: str):
    with open(path, 'wb') as f:
        _serialize(f, typesystem)


def save_to_string(typesystem: TypeSystem) -> str:
    f = BytesIO()
    _serialize(f, typesystem)
    return f.getvalue().decode('utf-8')


def _serialize(sink: IO, typesystem: TypeSystem):
    nsmap = {None: 'http://uima.apache.org/resourceSpecifier'}
    with etree.xmlfile(sink) as xf:
        with xf.element('typeSystemDescription', nsmap=nsmap):
            with xf.element('types'):
                for type in typesystem.get_types():
                    _serialize_type(xf, type)


def _serialize_type(xf: IO, type: Type):
    typeDescription = etree.Element('typeDescription')

    name = etree.SubElement(typeDescription, 'name')
    name.text = type.name

    description = etree.SubElement(typeDescription, 'description')
    description.text = type.description

    supertypeName = etree.SubElement(typeDescription, 'supertypeName')
    supertypeName.text = type.supertypeName

    features = etree.SubElement(typeDescription, 'features')
    for feature in type.features:
        _serialize_feature(features, feature)

    xf.write(typeDescription)


def _serialize_feature(features: etree.Element, feature: Feature):
    featureDescription = etree.SubElement(features, 'featureDescription')

    name = etree.SubElement(featureDescription, 'name')
    name.text = feature.name

    description = etree.SubElement(featureDescription, 'description')
    description.text = feature.description

    rangeTypeName = etree.SubElement(featureDescription, 'rangeTypeName')
    rangeTypeName.text = feature.rangeTypeName
