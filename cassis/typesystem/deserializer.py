from io import BytesIO
from typing import IO, Union

from lxml import etree

from cassis.typesystem.typesystem import TypeSystem, Type, Feature


def load_from_file(path: str) -> TypeSystem:
    return _parse(path)


def load_from_string(xml: str) -> TypeSystem:
    return _parse(BytesIO(xml.encode('utf-8')))


def _parse(source: Union[IO, str]) -> TypeSystem:
    """

    Args:
        source: a filename or file object containing XML data

    Returns:
        typesystem (TypeSystem):
    """
    types = []

    context = etree.iterparse(source, events=('end',), tag=('{*}typeDescription',))
    for event, elem in context:
        name = elem.find('{*}name').text or ''
        description = elem.find('{*}description').text or ''
        supertypeName = elem.find('{*}supertypeName').text or ''
        features = []

        for feature_description in elem.iterfind('{*}features/{*}featureDescription'):
            feature = _parse_feature(feature_description)
            features.append(feature)

        type = Type(name, description, supertypeName, features)
        types.append(type)

        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    del context

    return TypeSystem(types)


def _parse_feature(elem) -> Feature:
    name = elem.find('{*}name').text or ''
    description = elem.find('{*}description').text or ''
    rangeTypeName = elem.find('{*}rangeTypeName').text or ''
    return Feature(name, description, rangeTypeName)
