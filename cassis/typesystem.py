import re
from io import BytesIO
from typing import Callable, Dict, List, IO, Iterator, Union

import attr

from lxml import etree


def _string_to_valid_classname(name: str):
    return re.sub('[^a-zA-Z_]', '_', name)


@attr.s(slots=True)
class Annotation():
    type: str = attr.ib()
    begin: int = attr.ib()
    end: int = attr.ib()
    xmiID: int = attr.ib(default=None)
    sofa: int = attr.ib(default=None)


@attr.s(slots=True)
class Feature():
    name = attr.ib()
    description = attr.ib()
    rangeTypeName = attr.ib()


@attr.s(slots=True)
class Type():
    name: str = attr.ib()
    description: str = attr.ib()
    supertypeName: str = attr.ib()
    features: List[Feature] = attr.ib()
    constructor: Callable[[Dict], Annotation] = attr.ib(init=False, cmp=False, repr=False)

    def __attrs_post_init__(self):
        """ Build the constructor that can create annotations of this type """
        name = _string_to_valid_classname(self.name)
        fields = {feature.name: attr.ib(default=None) for feature in self.features}
        fields['type'] = attr.ib(default=self.name)
        self.constructor = attr.make_class(name, fields, bases=(Annotation,), slots=True)

    def __call__(self, **kwargs) -> Annotation:
        """ Creates an annotation of this type """
        return self.constructor(**kwargs)


class FallbackType():
    def __init__(self, **kwargs):
        self._fields = kwargs

    def __getattr__(self, item):
        return self._fields.get(item, None)


class TypeSystem():

    def __init__(self, types: List[Type] = None):
        if types is None:
            types = []

        self._types = {}
        for type in types:
            self._types[type.name] = type

    def has_type(self, typename: str):
        """

        Args:
            typename (str):

        Returns:

        """
        return typename in self._types

    def get_type(self, typename: str) -> Type:
        """

        Args:
            typename (str):

        Returns:

        """
        if self.has_type(typename):
            return self._types[typename]
        else:
            # TODO: Fix fallback for lenient parsing
            return FallbackType

    def get_types(self) -> Iterator[Type]:
        """ Returns all types of this type system """
        return iter(self._types.values())

    def to_xml(self, path_or_buf: Union[IO, str] = None):
        """ Creates a string representation of this type system

        Args:
            path_or_buf: File path or file-like object, if None is provided the result is returned as a string.

        Returns:

        """
        serializer = TypeSystemSerializer()

        if path_or_buf is None:
            sink = BytesIO()
            serializer.serialize(sink, self)
            return sink.getvalue().decode('utf-8')
        else:
            serializer.serialize(path_or_buf, self)

    def __len__(self) -> int:
        return len(self._types)


# Deserializing

def load_typesystem(source: Union[IO, str]) -> TypeSystem:
    deserializer = TypeSystemDeserializer()
    if isinstance(source, str):
        return deserializer.deserialize(BytesIO(source.encode('utf-8')))
    else:
        return deserializer.deserialize(source)


class TypeSystemDeserializer():

    def deserialize(self, source: Union[IO, str]) -> TypeSystem:
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
                feature = self._parse_feature(feature_description)
                features.append(feature)

            type = Type(name, description, supertypeName, features)
            types.append(type)

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context

        return TypeSystem(types)

    def _parse_feature(self, elem) -> Feature:
        name = elem.find('{*}name').text or ''
        description = elem.find('{*}description').text or ''
        rangeTypeName = elem.find('{*}rangeTypeName').text or ''
        return Feature(name, description, rangeTypeName)


# Serializing

class TypeSystemSerializer():

    def serialize(self, sink: Union[IO, str], typesystem: TypeSystem):
        nsmap = {None: 'http://uima.apache.org/resourceSpecifier'}
        with etree.xmlfile(sink) as xf:
            with xf.element('typeSystemDescription', nsmap=nsmap):
                with xf.element('types'):
                    for type in typesystem.get_types():
                        self._serialize_type(xf, type)

    def _serialize_type(self, xf: IO, type: Type):
        typeDescription = etree.Element('typeDescription')

        name = etree.SubElement(typeDescription, 'name')
        name.text = type.name

        description = etree.SubElement(typeDescription, 'description')
        description.text = type.description

        supertypeName = etree.SubElement(typeDescription, 'supertypeName')
        supertypeName.text = type.supertypeName

        features = etree.SubElement(typeDescription, 'features')
        for feature in type.features:
            self._serialize_feature(features, feature)

        xf.write(typeDescription)

    def _serialize_feature(self, features: etree.Element, feature: Feature):
        featureDescription = etree.SubElement(features, 'featureDescription')

        name = etree.SubElement(featureDescription, 'name')
        name.text = feature.name

        description = etree.SubElement(featureDescription, 'description')
        description.text = feature.description

        rangeTypeName = etree.SubElement(featureDescription, 'rangeTypeName')
        rangeTypeName.text = feature.rangeTypeName
