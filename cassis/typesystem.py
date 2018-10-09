from itertools import chain, filterfalse
from io import BytesIO
import re
from typing import Callable, Dict, List, IO, Iterator, Set, Union

import attr

from lxml import etree


def _string_to_valid_classname(name: str):
    return re.sub('[^a-zA-Z_]', '_', name)


@attr.s(slots=True)
class AnnotationBase:
    type: str = attr.ib()
    xmiID: int = attr.ib(default=None)


@attr.s(slots=True)
class Feature:
    name: str = attr.ib()
    rangeTypeName: str = attr.ib()
    description: str = attr.ib(default=None)


@attr.s(slots=True)
class Type:
    name: str = attr.ib()
    supertypeName: str = attr.ib()
    children: Set[str] = attr.ib(factory=set)
    features: Dict[str, Feature] = attr.ib(factory=dict)
    description: str = attr.ib(default=None)
    _inherited_features: Dict[str, Feature] = attr.ib(factory=dict)
    _constructor: Callable[[Dict], AnnotationBase] = attr.ib(init=False, cmp=False, repr=False)

    def __attrs_post_init__(self):
        """ Build the constructor that can create annotations of this type """
        name = _string_to_valid_classname(self.name)
        fields = {feature.name: attr.ib(default=None) for feature in chain(self.features.values(),
                                                                           self._inherited_features.values())}
        fields['type'] = attr.ib(default=self.name)

        self._constructor = attr.make_class(name, fields, bases=(AnnotationBase,), slots=True)

    def __call__(self, **kwargs) -> AnnotationBase:
        """ Creates an annotation of this type """
        return self._constructor(**kwargs)

    def get_feature(self, name: str) -> Feature:
        """ Find a feature by name

        This returns `None` if this type does not contain a feature
        with the given `name`.

        Args:
            name: The name of the feature

        Returns:
            The feature with name `name` or `None` if it does not exist.
        """
        return self.features.get(name, None)

    def add_feature(self, feature: Feature, inherited: bool = False):
        """ Add the given feature to his type.

        Args:
            feature: The feature
            inherited: Indicates whether this feature is inherited from a parent or not

        """
        target = self.features if not inherited else self._inherited_features

        if feature.name in target:
            msg = 'Feature with name [{0}] already exists in [{1}]!'.format(feature.name, self.name)
            raise ValueError(msg)
        target[feature.name] = feature

        # Recreate constructor to incorporate new features
        self.__attrs_post_init__()

    @property
    def all_features(self) -> Iterator[Feature]:
        return chain(self.features.values(), self._inherited_features.values())

class TypeSystem:

    TOP_TYPE_NAME = 'uima.cas.TOP'
    BASE_TYPE_NAME = 'uima.cas.AnnotationBase'
    ANNOTATION_TYPE_NAME = 'uima.tcas.Annotation'

    def __init__(self):
        self._types = {}

        # `top` is directly assigned in order to circumvent the inheritance
        top = Type(name=TypeSystem.TOP_TYPE_NAME, supertypeName=None)
        self._types[top.name] = top

        annotation_base = self.create_type(name=TypeSystem.BASE_TYPE_NAME, supertypeName=TypeSystem.TOP_TYPE_NAME)
        self.add_feature(annotation_base, 'sofa', rangeTypeName='uima.cas.Integer')

        annotation = self.create_type(name=TypeSystem.ANNOTATION_TYPE_NAME, supertypeName=annotation_base.name)
        self.add_feature(annotation, 'begin', rangeTypeName='uima.cas.Integer')
        self.add_feature(annotation, 'end', rangeTypeName='uima.cas.Integer')

    def has_type(self, typename: str):
        """

        Args:
            typename (str):

        Returns:

        """
        return typename in self._types

    def create_type(self, name: str, supertypeName: str = ANNOTATION_TYPE_NAME, description: str = None) -> Type:
        """ Create a new type and return it.

        Args:
            name: The name of the new type
            supertypeName: The name of the new types' supertype. Defaults to `uima.cas.AnnotationBase`
            description: The description of the new type

        Returns:
            The newly created type
        """
        if self.has_type(name):
            msg = 'Type with name [{0}] already exists!'.format(name)
            raise ValueError(msg)

        new_type = Type(name=name, supertypeName=supertypeName, description=description)

        if supertypeName != TypeSystem.TOP_TYPE_NAME:
            supertype = self.get_type(supertypeName)
            supertype.children.add(name)

            for feature in supertype.all_features:
                new_type.add_feature(feature, inherited=True)

        self._types[name] = new_type
        return new_type

    def get_type(self, typename: str) -> Type:
        """

        Args:
            typename (str):

        Returns:

        """
        if self.has_type(typename):
            return self._types[typename]
        else:
            raise Exception('Type with name [{0}] not found!'.format(typename))

    def get_types(self) -> Iterator[Type]:
        """ Returns all types of this type system """
        excluded = set([TypeSystem.TOP_TYPE_NAME, TypeSystem.BASE_TYPE_NAME, TypeSystem.ANNOTATION_TYPE_NAME])
        return filterfalse(lambda x: x.name in excluded, self._types.values())

    def add_feature(self, type_: Type, name: str, rangeTypeName: str, description: str = None):
        feature = Feature(name=name, rangeTypeName=rangeTypeName, description=description)
        type_.add_feature(feature)

        for child_name in type_.children:
            child_type = self.get_type(child_name)
            child_type.add_feature(feature, inherited=True)

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
        typesystem = TypeSystem()

        context = etree.iterparse(source, events=('end',), tag=('{*}typeDescription',))
        for event, elem in context:
            name = elem.find('{*}name').text or None
            description = elem.find('{*}description').text or None
            supertypeName = elem.find('{*}supertypeName').text or None
            features = []

            t = typesystem.create_type(name=name, description=description, supertypeName=supertypeName)

            # Parse features
            for feature_description in elem.iterfind('{*}features/{*}featureDescription'):
                name = feature_description.find('{*}name').text or None
                rangeTypeName = feature_description.find('{*}rangeTypeName').text or None
                description = feature_description.find('{*}description').text or None

                typesystem.add_feature(t, name=name, rangeTypeName=rangeTypeName, description=description)

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context

        return typesystem

# Serializing

class TypeSystemSerializer:

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
        for feature in type.features.values():
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
