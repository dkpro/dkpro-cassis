from collections import defaultdict
from itertools import chain, filterfalse
from io import BytesIO
from pathlib import Path
import re
from toposort import toposort_flatten
from typing import Callable, Dict, List, IO, Iterator, Optional, Set, Union
import warnings

from more_itertools import unique_everseen

import attr

from lxml import etree

PREDEFINED_TYPES = {
    "uima.cas.TOP",
    "uima.cas.Boolean",
    "uima.cas.Byte",
    "uima.cas.Short",
    "uima.cas.Integer",
    "uima.cas.Long",
    "uima.cas.Float",
    "uima.cas.Double",
    "uima.cas.String",
    "uima.cas.ArrayBase",
    "uima.cas.FSArray",
    "uima.cas.FloatArray",
    "uima.cas.IntegerArray",
    "uima.cas.StringArray",
    "uima.cas.ListBase",
    "uima.cas.FSList",
    "uima.cas.EmptyFSList",
    "uima.cas.NonEmptyFSList",
    "uima.cas.FloatList",
    "uima.cas.EmptyFloatList",
    "uima.cas.NonEmptyFloatList",
    "uima.cas.IntegerList",
    "uima.cas.EmptyIntegerList",
    "uima.cas.NonEmptyIntegerList",
    "uima.cas.StringList",
    "uima.cas.EmptyStringList",
    "uima.cas.NonEmptyStringList",
    "uima.cas.BooleanArray",
    "uima.cas.ByteArray",
    "uima.cas.ShortArray",
    "uima.cas.LongArray",
    "uima.cas.DoubleArray",
    "uima.cas.Sofa",
    "uima.cas.AnnotationBase",
    "uima.tcas.Annotation",
    "uima.tcas.DocumentAnnotation",
}

PRIMITIVE_TYPES = {
    "uima.cas.Boolean",
    "uima.cas.Byte",
    "uima.cas.Short",
    "uima.cas.Integer",
    "uima.cas.Long",
    "uima.cas.Float",
    "uima.cas.Double",
    "uima.cas.String",
}

COLLECTION_TYPES = {
    "uima.cas.ArrayBase",
    "uima.cas.FSArray",
    "uima.cas.FloatArray",
    "uima.cas.IntegerArray",
    "uima.cas.StringArray",
    "uima.cas.ListBase",
    "uima.cas.FSList",
    "uima.cas.EmptyFSList",
    "uima.cas.NonEmptyFSList",
    "uima.cas.FloatList",
    "uima.cas.EmptyFloatList",
    "uima.cas.NonEmptyFloatList",
    "uima.cas.IntegerList",
    "uima.cas.EmptyIntegerList",
    "uima.cas.NonEmptyIntegerList",
    "uima.cas.StringList",
    "uima.cas.EmptyStringList",
    "uima.cas.NonEmptyStringList",
    "uima.cas.BooleanArray",
    "uima.cas.ByteArray",
    "uima.cas.ShortArray",
    "uima.cas.LongArray",
    "uima.cas.DoubleArray",
}


PRIMITIVE_COLLECTION_TYPES = {
    "uima.cas.FloatArray",
    "uima.cas.IntegerArray",
    "uima.cas.StringArray",
    "uima.cas.FloatList",
    "uima.cas.EmptyFloatList",
    "uima.cas.NonEmptyFloatList",
    "uima.cas.IntegerList",
    "uima.cas.EmptyIntegerList",
    "uima.cas.NonEmptyIntegerList",
    "uima.cas.StringList",
    "uima.cas.EmptyStringList",
    "uima.cas.NonEmptyStringList",
    "uima.cas.BooleanArray",
    "uima.cas.ByteArray",
    "uima.cas.ShortArray",
    "uima.cas.LongArray",
    "uima.cas.DoubleArray",
}


def _string_to_valid_classname(name: str):
    return re.sub("[^a-zA-Z0-9_]", "_", name)


@attr.s(slots=True, cmp=False)
class FeatureStructure:
    """The base class for all feature structure instances"""

    type = attr.ib()  # str: Type name of this feature structure instance
    xmiID = attr.ib(default=None)  # int: xmiID of this feature structure instance

    def __eq__(self, other):
        return self.__slots__ == other.__slots__


@attr.s(slots=True)
class Feature:
    """A feature defines one attribute of a feature structure"""

    name = attr.ib()  # type: str
    rangeTypeName = attr.ib()  # type: str
    description = attr.ib(default=None)  # type: str
    elementType = attr.ib(default=None)  # type: str
    multipleReferencesAllowed = attr.ib(default=None)  # type: bool


@attr.s(slots=True)
class Type:
    """ Describes types in a type system.

    Instances of this class should not be created by hand, instead the type 
    system's `create_type` should be used.

    """

    name = attr.ib()  # type: str #: Type name of this type
    supertypeName = attr.ib()  # type: str # : Name of the super type
    description = attr.ib(default=None)  # type: str #: Description of this type
    _children = attr.ib(factory=set)  # type: Set[str]
    _features = attr.ib(factory=dict)  # type: Dict[str, Feature]
    _inherited_features = attr.ib(factory=dict)  # type: Dict[str, Feature]
    _constructor = attr.ib(init=False, cmp=False, repr=False)  # type: Callable[[Dict], FeatureStructure]

    def __attrs_post_init__(self):
        """ Build the constructor that can create feature structures of this type """
        name = _string_to_valid_classname(self.name)
        fields = {feature.name: attr.ib(default=None) for feature in self.all_features}
        fields["type"] = attr.ib(default=self.name)

        self._constructor = attr.make_class(name, fields, bases=(FeatureStructure,), slots=True, cmp=False)

    def __call__(self, **kwargs) -> FeatureStructure:
        """ Creates an feature structure of this type
        
        When called with keyword arguments whose keys are the feature names and values are the 
        respective feature values, then a new feature structure instance is created.

        Returns:
            A new feature structure instance of this type.

        """
        return self._constructor(**kwargs)

    def get_feature(self, name: str) -> Optional[Feature]:
        """ Find a feature by name

        This returns `None` if this type does not contain a feature
        with the given `name`.

        Args:
            name: The name of the feature

        Returns:
            The feature with name `name` or `None` if it does not exist.
        """
        return self._features.get(name, None)

    def add_feature(self, feature: Feature, inherited: bool = False):
        """ Add the given feature to his type.

        Args:
            feature: The feature
            inherited: Indicates whether this feature is inherited from a parent or not

        """
        target = self._features if not inherited else self._inherited_features

        # Check that feature is not defined in on current type
        if feature.name in target:
            msg = "Feature with name [{0}] already exists in [{1}]!".format(feature.name, self.name)
            raise ValueError(msg)

        # Check that feature is not redefined on parent type
        if feature.name in self._inherited_features:
            redefined_feature = self._inherited_features[feature.name]

            if redefined_feature == feature:
                msg = "Feature with name [{0}] already exists in parent!".format(feature.name)
                warnings.warn(msg)
            else:
                msg = "Feature with name [{0}] already exists in parent but is redefined!".format(feature.name)
                raise ValueError(msg)

        target[feature.name] = feature

        # Recreate constructor to incorporate new features
        self.__attrs_post_init__()

    @property
    def features(self) -> Iterator[Feature]:
        """ Returns an iterator over the features of this type. Inherited features are excluded. To
        find these in addition to this types' own features, use `all_features`.

        Returns:
            An iterator over all features of this type, excluding inherited ones

        """
        return iter(self._features.values())

    @property
    def all_features(self) -> Iterator[Feature]:
        """ Returns an iterator over the features of this type. Inherited features are included. To
        just retrieve immediate features, use `features`.

        Returns:
            An iterator over all features of this type, including inherited ones

        """

        # We use `unique_everseen` here, as children could redefine parent types (Issue #56)
        return unique_everseen(chain(self._features.values(), self._inherited_features.values()))


class TypeSystem:
    TOP_TYPE_NAME = "uima.cas.TOP"

    def __init__(self):
        self._types = {}

        # We store types that are predefined but still defined in the typesystem here
        # In order to restore them when serializing
        self._predefined_types = set()

        # The type system of a UIMA CAS has several predefined types. These are
        # added in the following

        # `top` is directly assigned in order to circumvent the inheritance
        top = Type(name=TypeSystem.TOP_TYPE_NAME, supertypeName=None)
        self._types[top.name] = top

        # Primitive types
        self.create_type(name="uima.cas.Boolean", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.Byte", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.Short", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.Integer", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.Long", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.Float", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.Double", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.String", supertypeName="uima.cas.TOP")

        # Array
        t = self.create_type(name="uima.cas.ArrayBase", supertypeName="uima.cas.TOP")
        self.add_feature(t, name="elements", rangeTypeName="uima.cas.TOP", multipleReferencesAllowed=True)

        self.create_type(name="uima.cas.FSArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.BooleanArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.ByteArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.ShortArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.LongArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.DoubleArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.FloatArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.IntegerArray", supertypeName="uima.cas.ArrayBase")
        self.create_type(name="uima.cas.StringArray", supertypeName="uima.cas.ArrayBase")

        # List
        self.create_type(name="uima.cas.ListBase", supertypeName="uima.cas.TOP")
        self.create_type(name="uima.cas.FSList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyFSList", supertypeName="uima.cas.FSList")
        t = self.create_type(name="uima.cas.NonEmptyFSList", supertypeName="uima.cas.FSList")
        self.add_feature(t, name="head", rangeTypeName="uima.cas.TOP", multipleReferencesAllowed=True)
        self.add_feature(t, name="tail", rangeTypeName="uima.cas.FSList", multipleReferencesAllowed=True)

        # FloatList
        self.create_type(name="uima.cas.FloatList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyFloatList", supertypeName="uima.cas.FloatList")
        t = self.create_type(name="uima.cas.NonEmptyFloatList", supertypeName="uima.cas.FloatList")
        self.add_feature(t, name="head", rangeTypeName="uima.cas.Float")
        self.add_feature(t, name="tail", rangeTypeName="uima.cas.FloatList", multipleReferencesAllowed=True)

        # IntegerList
        self.create_type(name="uima.cas.IntegerList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyIntegerList", supertypeName="uima.cas.IntegerList")
        t = self.create_type(name="uima.cas.NonEmptyIntegerList", supertypeName="uima.cas.IntegerList")
        self.add_feature(t, name="head", rangeTypeName="uima.cas.Integer")
        self.add_feature(t, name="tail", rangeTypeName="uima.cas.IntegerList", multipleReferencesAllowed=True)

        # StringList
        self.create_type(name="uima.cas.StringList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyStringList", supertypeName="uima.cas.StringList")
        t = self.create_type(name="uima.cas.NonEmptyStringList", supertypeName="uima.cas.StringList")
        self.add_feature(t, name="head", rangeTypeName="uima.cas.String")
        self.add_feature(t, name="tail", rangeTypeName="uima.cas.StringList", multipleReferencesAllowed=True)

        # Sofa
        t = self.create_type(name="uima.cas.Sofa", supertypeName="uima.cas.TOP")
        self.add_feature(t, name="sofaNum", rangeTypeName="uima.cas.Integer")
        self.add_feature(t, name="sofaID", rangeTypeName="uima.cas.String")
        self.add_feature(t, name="mimeType", rangeTypeName="uima.cas.String")
        self.add_feature(t, name="sofaArray", rangeTypeName="uima.cas.TOP", multipleReferencesAllowed=True)
        self.add_feature(t, name="sofaString", rangeTypeName="uima.cas.String")
        self.add_feature(t, name="sofaURI", rangeTypeName="uima.cas.String")

        # AnnotationBase
        t = self.create_type(name="uima.cas.AnnotationBase", supertypeName="uima.cas.TOP")
        self.add_feature(t, name="sofa", rangeTypeName="uima.cas.Sofa")

        # Annotation
        t = self.create_type(name="uima.tcas.Annotation", supertypeName="uima.cas.AnnotationBase")
        self.add_feature(t, name="begin", rangeTypeName="uima.cas.Integer")
        self.add_feature(t, name="end", rangeTypeName="uima.cas.Integer")

        # DocumentAnnotation
        t = self.create_type(name="uima.tcas.DocumentAnnotation", supertypeName="uima.tcas.Annotation")
        self.add_feature(t, name="language", rangeTypeName="uima.cas.String")

    def has_type(self, typename: str):
        """ Checks whether this type system contains a type with name `typename`.

        Args:
            typename: The name of type whose existence is to be checked.

        Returns:
            `True` if a type with `typename` exists, else `False`.
        """
        return typename in self._types

    def create_type(self, name: str, supertypeName: str = "uima.tcas.Annotation", description: str = None) -> Type:
        """ Creates a new type and return it.

        Args:
            name: The name of the new type
            supertypeName: The name of the new types' supertype. Defaults to `uima.cas.AnnotationBase`
            description: The description of the new type

        Returns:
            The newly created type
        """
        if self.has_type(name) and name not in PREDEFINED_TYPES:
            msg = "Type with name [{0}] already exists!".format(name)
            raise ValueError(msg)

        new_type = Type(name=name, supertypeName=supertypeName, description=description)

        if supertypeName != TypeSystem.TOP_TYPE_NAME:
            supertype = self.get_type(supertypeName)
            supertype._children.add(name)

            for feature in supertype.all_features:
                new_type.add_feature(feature, inherited=True)

        self._types[name] = new_type
        return new_type

    def get_type(self, typename: str) -> Type:
        """ Finds a type by name in the type system of this CAS.

        Args:
            typename: The name of the type to retrieve

        Returns:
            The type with name `typename`
        Raises:
            Exception: If no type with `typename` could be found.
        """
        if self.has_type(typename):
            return self._types[typename]
        else:
            raise Exception("Type with name [{0}] not found!".format(typename))

    def get_types(self) -> Iterator[Type]:
        """ Returns all types of this type system """
        return filterfalse(lambda x: x.name in PREDEFINED_TYPES, self._types.values())

    def is_primitive(self, type_name: str) -> bool:
        """ Checks if the type identified by `type_name` is a primitive type.

        Args:
            type_name: The name of the type to query for.
        Returns:
            Returns True if the type identified by `type_name` is a primitive type, else False
        """
        return type_name in PRIMITIVE_TYPES

    def is_collection(self, type_name: str) -> bool:
        """ Checks if the type identified by `type_name` is a collection, e.g. list or array.

        Args:
            type_name: The name of the type to query for.
        Returns:
            Returns True if the type identified by `type_name` is a collection type, else False
        """
        return type_name in COLLECTION_TYPES

    def is_primitive_collection(self, type_name) -> bool:
        """ Checks if the type identified by `type_name` is a primitive collection, e.g. list or array of primitives.

        Args:
            type_name: The name of the type to query for.
        Returns:
            Returns True if the type identified by `type_name` is a primitive collection type, else False
        """
        return type_name in PRIMITIVE_COLLECTION_TYPES

    def add_feature(
        self,
        type_: Type,
        name: str,
        rangeTypeName: str,
        elementType: str = None,
        description: str = None,
        multipleReferencesAllowed: bool = None,
    ):
        """ Adds a feature to the given type.

        Args:
            type_: The type to which the feature will be added
            name: The name of the new feature
            rangeTypeName: The feature's rangeTypeName specifies the type of value that the feature can take.
            elementType: The elementType of a feature is optional, and applies only when the rangeTypeName
                is uima.cas.FSArray or uima.cas.FSList The elementType specifies what type of value can be
                assigned as an element of the array or list.
            description: The description of the new feature
            multipleReferencesAllowed: Setting this to true indicates that the array or list may be shared,
                so changes to it may affect other objects in the CAS.

        Raises:
            Exception: If a feature with name `name` already exists in `type_`.
        """
        feature = Feature(
            name=name,
            rangeTypeName=rangeTypeName,
            elementType=elementType,
            description=description,
            multipleReferencesAllowed=multipleReferencesAllowed,
        )
        type_.add_feature(feature)

        for child_name in type_._children:
            child_type = self.get_type(child_name)
            child_type.add_feature(feature, inherited=True)

    def to_xml(self, path: Union[str, Path, None] = None) -> Optional[str]:
        """Creates a XMI representation of this type system.

        Args:
            path: File path or file-like object, if `None` is provided the result is returned as a string.

        Returns:
            If `path` is None, then the XML representation of this type system is returned as a string.

        """
        serializer = TypeSystemSerializer()

        # If `path` is None, then serialize to a string and return it
        if path is None:
            sink = BytesIO()
            serializer.serialize(sink, self)
            return sink.getvalue().decode("utf-8")
        elif isinstance(path, str):
            with open(path, "wb") as f:
                serializer.serialize(f, self)
        elif isinstance(path, Path):
            with path.open("wb") as f:
                serializer.serialize(f, self)
        else:
            raise TypeError("`path` needs to be one of [str, None, Path], but was <{0}>".format(type(path)))

    def _defines_predefined_type(self, type_name):
        self._predefined_types.add(type_name)


# Deserializing


def load_typesystem(source: Union[IO, str]) -> TypeSystem:
    """ Loads a type system from a XML source.

    Args:
        source: The XML source. If `source` is a string, then it is assumed to be an XML string.
                If `source` is a file-like object, then the data is read from it.

    Returns:
        The deserialized type system

    """
    deserializer = TypeSystemDeserializer()
    if isinstance(source, str):
        return deserializer.deserialize(BytesIO(source.encode("utf-8")))
    else:
        return deserializer.deserialize(source)


class TypeSystemDeserializer:
    def deserialize(self, source: Union[IO, str]) -> TypeSystem:
        """

        Args:
            source: a filename or file object containing XML data

        Returns:
            typesystem (TypeSystem):
        """

        # It can be that the types in the xml are listed out-of-order, that means
        # some type A appears before its supertype. In order to deserialize these
        # files properly without sacrificing the requirement that the supertype
        # of a type needs to already be present, we sort the graph of types and
        # supertypes topologically. This means a supertype will always be inserted
        # before its children. The inheritance relation is expressed in the
        # `dependencies` dictionary.
        types = {}
        features = defaultdict(list)
        dependencies = defaultdict(set)

        context = etree.iterparse(source, events=("end",), tag=("{*}typeDescription",))
        for event, elem in context:
            type_name = self._get_elem_as_str(elem.find("{*}name"))

            if "." not in type_name:
                type_name = "uima.noNamespace." + type_name

            description = self._get_elem_as_str(elem.find("{*}description"))
            supertypeName = self._get_elem_as_str(elem.find("{*}supertypeName"))

            types[type_name] = Type(name=type_name, supertypeName=supertypeName, description=description)
            dependencies[type_name].add(supertypeName)

            # Parse features
            for fd in elem.iterfind("{*}features/{*}featureDescription"):
                feature_name = self._get_elem_as_str(fd.find("{*}name"))
                rangeTypeName = self._get_elem_as_str(fd.find("{*}rangeTypeName"))
                description = self._get_elem_as_str(fd.find("{*}description"))
                multipleReferencesAllowed = self._get_elem_as_bool(fd.find("{*}multipleReferencesAllowed"))
                elementType = self._get_elem_as_str(fd.find("{*}elementType"))

                f = Feature(
                    name=feature_name,
                    rangeTypeName=rangeTypeName,
                    description=description,
                    multipleReferencesAllowed=multipleReferencesAllowed,
                    elementType=elementType,
                )
                features[type_name].append(f)

                # The feature range also uses type information which has to
                # be included in the dependency relation
                dependencies[type_name].add(rangeTypeName)

            # Free the XML tree element from memory as it is not needed anymore
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context

        ts = TypeSystem()

        # Some CAS handling libraries add predefined types to the typesystem XML, e.g. DocumentAnnotation.
        # Here we check that the redefinition of predefined types adheres to the definition in UIMA
        for type_name, t in types.items():
            if type_name in PREDEFINED_TYPES:
                pt = ts.get_type(type_name)

                t_features = list(sorted(features[type_name]))
                pt_features = list(sorted(pt.features))

                if t.supertypeName != pt.supertypeName:
                    msg = "Redefining predefined type [{0}] with different superType [{1}], expected [{2}]"
                    raise ValueError(msg.format(type_name, t.supertypeName, pt.supertypeName))

                # We check whether the predefined type is defined the same in UIMA and this typesystem
                if t_features == pt_features:
                    # No need to create predefined types, but store them for serialization
                    ts._defines_predefined_type(type_name)
                    continue
                else:
                    msg = "Redefining predefined type [{0}] with different features: {1} - Have to be {2}"
                    raise ValueError(msg.format(type_name, t_features, pt_features))

        # Add the types to the type system in order of dependency (parents before children)
        for type_name in toposort_flatten(dependencies, sort=False):
            # No need to recreate predefined types
            if type_name in PREDEFINED_TYPES:
                continue

            t = types[type_name]
            created_type = ts.create_type(name=t.name, description=t.description, supertypeName=t.supertypeName)

            for f in features[t.name]:
                ts.add_feature(
                    created_type,
                    name=f.name,
                    rangeTypeName=f.rangeTypeName,
                    elementType=f.elementType,
                    description=f.description,
                )

        return ts

    def _get_elem_as_str(self, elem: etree.Element) -> Optional[str]:
        if elem is not None:
            return elem.text
        else:
            return None

    def _get_elem_as_bool(self, elem: etree.Element) -> Optional[bool]:
        if elem is not None:
            return bool(elem.text)
        else:
            return None


# Serializing


class TypeSystemSerializer:
    def serialize(self, sink: Union[IO, str], typesystem: TypeSystem):
        nsmap = {None: "http://uima.apache.org/resourceSpecifier"}
        with etree.xmlfile(sink) as xf:
            with xf.element("typeSystemDescription", nsmap=nsmap):
                with xf.element("types"):
                    # In order to export the same types that we imported, we
                    # also emit the (redundant) predefined types
                    for predefined_type_name in sorted(typesystem._predefined_types):
                        predefined_type = typesystem.get_type(predefined_type_name)
                        self._serialize_type(xf, predefined_type)

                    for type_ in sorted(typesystem.get_types(), key=lambda t: t.name):
                        self._serialize_type(xf, type_)

    def _serialize_type(self, xf: IO, type_: Type):
        typeDescription = etree.Element("typeDescription")

        name = etree.SubElement(typeDescription, "name")
        type_name = type_.name
        if type_name.startswith("uima.noNamespace."):
            type_name = type_name.replace("uima.noNamespace.", "")

        name.text = type_name

        description = etree.SubElement(typeDescription, "description")
        description.text = type_.description

        supertypeName = etree.SubElement(typeDescription, "supertypeName")
        supertypeName.text = type_.supertypeName

        # Only create the `feature` element if there is at least one feature
        feature_list = list(type_.features)
        if feature_list:
            features = etree.SubElement(typeDescription, "features")
            for feature in feature_list:
                self._serialize_feature(features, feature)

        xf.write(typeDescription)

    def _serialize_feature(self, features: etree.Element, feature: Feature):
        featureDescription = etree.SubElement(features, "featureDescription")

        name = etree.SubElement(featureDescription, "name")
        name.text = feature.name

        description = etree.SubElement(featureDescription, "description")
        description.text = feature.description

        rangeTypeName = etree.SubElement(featureDescription, "rangeTypeName")
        rangeTypeName.text = feature.rangeTypeName

        if feature.multipleReferencesAllowed is not None:
            multipleReferencesAllowed = etree.SubElement(featureDescription, "multipleReferencesAllowed")
            multipleReferencesAllowed.text = "true" if feature.multipleReferencesAllowed else "false"

        if feature.elementType is not None:
            elementType = etree.SubElement(featureDescription, "elementType")
            elementType.text = feature.elementType
