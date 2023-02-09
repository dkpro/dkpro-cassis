import re
import warnings
from collections import defaultdict
from copy import copy
from enum import Enum, auto
from io import BytesIO
from itertools import chain, filterfalse
from pathlib import Path
from typing import IO, Any, Callable, Dict, Iterator, List, Optional, Set, Union

import attr
from deprecation import deprecated
from lxml import etree
from more_itertools import unique_everseen
from toposort import toposort_flatten

TOP_TYPE_NAME = "uima.cas.TOP"

NAMESPACE_SEPARATOR = "."

NAME_SPACE_UIMA_CAS = "uima" + NAMESPACE_SEPARATOR + "cas"
UIMA_CAS_PREFIX = NAME_SPACE_UIMA_CAS + NAMESPACE_SEPARATOR
TYPE_NAME_TOP = UIMA_CAS_PREFIX + "TOP"
TYPE_NAME_INTEGER = UIMA_CAS_PREFIX + "Integer"
TYPE_NAME_FLOAT = UIMA_CAS_PREFIX + "Float"
TYPE_NAME_STRING = UIMA_CAS_PREFIX + "String"
TYPE_NAME_BOOLEAN = UIMA_CAS_PREFIX + "Boolean"
TYPE_NAME_BYTE = UIMA_CAS_PREFIX + "Byte"
TYPE_NAME_SHORT = UIMA_CAS_PREFIX + "Short"
TYPE_NAME_LONG = UIMA_CAS_PREFIX + "Long"
TYPE_NAME_DOUBLE = UIMA_CAS_PREFIX + "Double"
TYPE_NAME_ARRAY_BASE = UIMA_CAS_PREFIX + "ArrayBase"
TYPE_NAME_FS_ARRAY = UIMA_CAS_PREFIX + "FSArray"
TYPE_NAME_FS_LIST = UIMA_CAS_PREFIX + "FSList"
TYPE_NAME_EMPTY_FS_LIST = UIMA_CAS_PREFIX + "EmptyFSList"
TYPE_NAME_NON_EMPTY_FS_LIST = UIMA_CAS_PREFIX + "NonEmptyFSList"
TYPE_NAME_INTEGER_ARRAY = UIMA_CAS_PREFIX + "IntegerArray"
TYPE_NAME_INTEGER_LIST = UIMA_CAS_PREFIX + "IntegerList"
TYPE_NAME_EMPTY_INTEGER_LIST = UIMA_CAS_PREFIX + "EmptyIntegerList"
TYPE_NAME_NON_EMPTY_INTEGER_LIST = UIMA_CAS_PREFIX + "NonEmptyIntegerList"
TYPE_NAME_FLOAT_ARRAY = UIMA_CAS_PREFIX + "FloatArray"
TYPE_NAME_FLOAT_LIST = UIMA_CAS_PREFIX + "FloatList"
TYPE_NAME_EMPTY_FLOAT_LIST = UIMA_CAS_PREFIX + "EmptyFloatList"
TYPE_NAME_NON_EMPTY_FLOAT_LIST = UIMA_CAS_PREFIX + "NonEmptyFloatList"
TYPE_NAME_STRING_ARRAY = UIMA_CAS_PREFIX + "StringArray"
TYPE_NAME_STRING_LIST = UIMA_CAS_PREFIX + "StringList"
TYPE_NAME_EMPTY_STRING_LIST = UIMA_CAS_PREFIX + "EmptyStringList"
TYPE_NAME_NON_EMPTY_STRING_LIST = UIMA_CAS_PREFIX + "NonEmptyStringList"
TYPE_NAME_BOOLEAN_ARRAY = UIMA_CAS_PREFIX + "BooleanArray"
TYPE_NAME_BYTE_ARRAY = UIMA_CAS_PREFIX + "ByteArray"
TYPE_NAME_SHORT_ARRAY = UIMA_CAS_PREFIX + "ShortArray"
TYPE_NAME_LONG_ARRAY = UIMA_CAS_PREFIX + "LongArray"
TYPE_NAME_DOUBLE_ARRAY = UIMA_CAS_PREFIX + "DoubleArray"
TYPE_NAME_FS_HASH_SET = UIMA_CAS_PREFIX + "FSHashSet"
TYPE_NAME_ANNOTATION_BASE = UIMA_CAS_PREFIX + "AnnotationBase"

TYPE_NAME_SOFA = UIMA_CAS_PREFIX + "Sofa"
FEATURE_BASE_NAME_SOFANUM = "sofaNum"
FEATURE_BASE_NAME_SOFAID = "sofaID"
FEATURE_BASE_NAME_SOFAMIME = "mimeType"
FEATURE_BASE_NAME_SOFAURI = "sofaURI"
FEATURE_BASE_NAME_SOFASTRING = "sofaString"
FEATURE_BASE_NAME_SOFAARRAY = "sofaArray"

NAME_SPACE_UIMA_TCAS = "uima" + NAMESPACE_SEPARATOR + "tcas"
UIMA_TCAS_PREFIX = NAME_SPACE_UIMA_TCAS + NAMESPACE_SEPARATOR
TYPE_NAME_ANNOTATION = UIMA_TCAS_PREFIX + "Annotation"
TYPE_NAME_DOCUMENT_ANNOTATION = UIMA_TCAS_PREFIX + "DocumentAnnotation"
FEATURE_BASE_NAME_SOFA = "sofa"
FEATURE_BASE_NAME_BEGIN = "begin"
FEATURE_BASE_NAME_END = "end"
FEATURE_BASE_NAME_LANGUAGE = "language"
FEATURE_BASE_NAME_HEAD = "head"
FEATURE_BASE_NAME_TAIL = "tail"

_DOCUMENT_ANNOTATION_TYPE = "uima.tcas.DocumentAnnotation"

_PREDEFINED_TYPES = {
    "uima.cas.TOP",
    "uima.cas.NULL",
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
}

_PRIMITIVE_TYPES = {
    "uima.cas.Boolean",
    "uima.cas.Byte",
    "uima.cas.Short",
    "uima.cas.Integer",
    "uima.cas.Long",
    "uima.cas.Float",
    "uima.cas.Double",
    "uima.cas.String",
}

_COLLECTION_TYPES = {
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

_PRIMITIVE_COLLECTION_TYPES = {
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

_PRIMITIVE_ARRAY_TYPES = {
    "uima.cas.FloatArray",
    "uima.cas.IntegerArray",
    "uima.cas.BooleanArray",
    "uima.cas.ByteArray",
    "uima.cas.ShortArray",
    "uima.cas.LongArray",
    "uima.cas.DoubleArray",
    "uima.cas.StringArray",
}

_PRIMITIVE_LIST_TYPES = {TYPE_NAME_INTEGER_LIST, TYPE_NAME_FLOAT_LIST, TYPE_NAME_STRING_LIST}

_INHERITANCE_FINAL_TYPES = _PRIMITIVE_ARRAY_TYPES

_ARRAY_TYPES = _PRIMITIVE_ARRAY_TYPES | {TYPE_NAME_FS_ARRAY}

_LIST_TYPES = _PRIMITIVE_LIST_TYPES | {TYPE_NAME_FS_LIST}


class TypeSystemMode(Enum):
    """How much type system information to include."""

    FULL = auto()
    MINIMAL = auto()
    NONE = auto()


def _string_to_valid_classname(name: str):
    return re.sub("[^a-zA-Z0-9_]", "_", name)


def is_predefined(type_: Union[str, "Type"]) -> bool:
    """Checks if the given type  is predefined by UIMA and by default in a new type system.

    Args:
        type_: The type to check
    Returns:
        Returns True if the given type is predefined, else False
    """
    type_name = type_ if isinstance(type_, str) else type_.name
    return type_name in _PREDEFINED_TYPES


def is_collection(type_: Union[str, "Type"], feature: "Feature") -> bool:
    """Checks if the given feature for the type identified by `type` is a collection, e.g. list or array.

    Args:
        type_: The type to which the feature belongs (`Type` or name as string)
        feature: The feature to query for.
    Returns:
        Returns True if the given feature is a collection type, else False
    """
    type_name = type_ if isinstance(type_, str) else type_.name

    if type_name in _COLLECTION_TYPES and feature.name == "elements":
        return True
    else:
        return feature.rangeType.name in _COLLECTION_TYPES


def is_primitive(type_: "Type") -> bool:
    """Checks if the type identified by `type` is a primitive type.

    Args:
        type_: Type to query for
    Returns:
        Returns True if the type identified by `type` is a primitive type, else False
    """
    type_name = type_.name

    if type_name == TOP_TYPE_NAME:
        return False
    elif type_name in _PRIMITIVE_TYPES:
        return True
    else:
        return is_primitive(type_.supertype)


def is_primitive_collection(type_: "Type") -> bool:
    """Checks if the type identified by `type` is a primitive collection, e.g. list or array of primitives.

    Args:
        type_: Type to query for
    Returns:
        Returns True if the type identified by `type` is a primitive collection type, else False
    """
    type_name = type_.name

    if type_name == TOP_TYPE_NAME:
        return False
    elif type_name in _PRIMITIVE_COLLECTION_TYPES:
        return True
    else:
        return is_primitive_collection(type_.supertype)


def is_primitive_array(type_: Union[str, "Type"]) -> bool:
    """Checks if the type identified by `type` is a primitive array, e.g. array of primitives.

    Args:
        type_: Type to query for (`Type` or name as string)
    Returns:
        Returns `True` if the type identified by `type` is a primitive array type, else `False`
    """
    type_name = type_ if isinstance(type_, str) else type_.name

    if type_name == TOP_TYPE_NAME:
        return False

    # Arrays are inheritance-final, so we do not need to check the inheritance hierarchy
    return type_name in _PRIMITIVE_ARRAY_TYPES


def is_primitive_list(type_: Union[str, "Type"]) -> bool:
    """Checks if the type identified by `type` is a primitive list, e.g. list of primitives.

    Args:
        type_: Type to query for (`Type` or name as string)
    Returns:
        Returns `True` if the type identified by `type` is a primitive array type, else `False`
    """
    type_name = type_ if isinstance(type_, str) else type_.name

    if type_name == TOP_TYPE_NAME:
        return False

    # Arrays are inheritance-final, so we do not need to check the inheritance hierarchy
    return type_name in _PRIMITIVE_LIST_TYPES


def is_array(type_: Union[str, "Type"]) -> bool:
    """Checks if the type identified by `type` is an array.

    Args:
        type_: Type to query for (`Type` or name as string)
    Returns:
        Returns `True` if the type identified by `type` is an array type, else `False`
    """
    type_name = type_ if isinstance(type_, str) else type_.name

    if type_name == TOP_TYPE_NAME:
        return False

    # Arrays are inheritance-final, so we do not need to check the inheritance hierarchy
    return type_name in _ARRAY_TYPES


def is_list(type_: Union[str, "Type"]) -> bool:
    """Checks if the type identified by `type` is a list.

    Args:
        type_: Type to query for (`Type` or name as string)
    Returns:
        Returns `True` if the type identified by `type` is a list type, else `False`
    """
    type_name = type_ if isinstance(type_, str) else type_.name

    if type_name == TOP_TYPE_NAME:
        return False

    # Lists are inheritance-final, so we do not need to check the inheritance hierarchy
    return type_name in _LIST_TYPES


@attr.s
class TypeCheckError(Exception):
    xmiID: int = attr.ib()  # xmiID of the feature structure with type error
    description: str = attr.ib()  # Description of the type check error


@attr.s
class TypeNotFoundError(Exception):
    message: str = attr.ib()  # Description of the error


@attr.s
class AnnotationHasNoSofa(Exception):
    message: str = attr.ib()  # Description of the error


@attr.s(slots=True, hash=False, eq=True, order=True, repr=False)
class FeatureStructure:
    """The base class for all feature structure instances"""

    type: "Type" = attr.ib()  # Type name of this feature structure instance
    xmiID: int = attr.ib(default=None, eq=False)  # xmiID of this feature structure instance

    def value(self, name: str):
        """Returns the value of the feature `name`."""
        return getattr(self, name)

    def get_covered_text(self) -> str:
        """Gets the text that is covered by this feature structure iff it is associated with a sofa and has a begin/end.

        Returns:
            The text covered by the annotation

        """
        if hasattr(self, "sofa") and hasattr(self, "begin") and hasattr(self, "end"):
            if self.sofa is None:
                raise AnnotationHasNoSofa(
                    "Annotations must have a SofA (be added to a CAS) before get_covered_text() can be called"
                )
            if self.sofa.sofaString is None:
                return None
            return self.sofa.sofaString[self.begin : self.end]
        else:
            raise NotImplementedError()

    def get(self, path: str) -> Optional[Any]:
        """Recursively gets an attribute, e.g. fs.get("a.b.c") would return attribute `c` of `b` of `a`.

        If you have nested feature structures, e.g. a feature structure with feature `a` that has a feature `b` that
        has a feature `c`, some of which can be `None`, then you can use the following:

            fs.get("a.b.c")
        """
        if not isinstance(path, str):
            raise AttributeError(f"Feature path [{path}] must be a string but is a [{type(path)}]")

        cur = self
        for part in path.split("."):
            cur = getattr(cur, part, None)
            if cur is None:
                return None

        return cur

    def set(self, path: str, value: Any):
        """Recursively sets an attribute, e.g. fs.set("a.b.c", 42) would set attribute `c` of `b` of `a` to `42`."""

        if "." not in path:
            setattr(self, path, value)
            return

        idx = path.rindex(".")

        value_name = path[idx + 1 :]
        path = path[:idx]

        target = self.get(path)

        if target is None:
            raise AttributeError(f"Attribute with name [{value_name}] not found on: {target}")

        setattr(target, value_name, value)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __hash__(self):
        return self.xmiID

    def __eq__(self, other):
        return self.__slots__ == other.__slots__

    def __str__(self):
        def _abbreviate_type_name(type_name: str):
            """Turns long type names like `de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token` to
            something shorter like `d.t.u.d.c.a.s.t.Token`.
            """
            parts = type_name.split(".")
            result = []
            for part in parts[:-1]:
                result.append(part[0])
            result.append(parts[-1])
            return ".".join(result)

        values = {}
        for feature in self.type.all_features:
            name = feature.name
            value = getattr(self, name)

            if value is not None and name not in {"sofa", "parent", "type"}:
                values[name] = value

        s = ", ".join(f"{n}={v}" for n, v in sorted(values.items()))
        return f"{_abbreviate_type_name(self.type.name)}({s})"

    def __repr__(self):
        return str(self)


@attr.s(slots=True, eq=False, order=False, repr=False)
class Feature:
    """A feature defines one attribute of a feature structure"""

    name: str = attr.ib()
    domainType: "Type" = attr.ib()
    rangeType: "Type" = attr.ib()
    description: str = attr.ib(default=None)
    elementType: "Type" = attr.ib(default=None)
    multipleReferencesAllowed: bool = attr.ib(default=None)
    _has_reserved_name: bool = attr.ib(default=False)

    def __eq__(self, other):
        if not isinstance(other, Feature):
            return False

        if self.name != other.name or self.description != other.description:
            return False

        if self.rangeType.name != other.rangeType.name:
            return False

        # If elementType is `None`, then we assume the default is `TOP`
        element_type_name = self.elementType.name if self.elementType else None
        other_element_type_name = other.elementType.name if other.elementType else None
        if (element_type_name or TOP_TYPE_NAME) != (other_element_type_name or TOP_TYPE_NAME):
            return False

        # If multipleReferencesAllowed is `None`, then we assume the default is `False`
        self_multiref = False if self.multipleReferencesAllowed is None else self.multipleReferencesAllowed
        other_multiref = False if self.multipleReferencesAllowed is None else self.multipleReferencesAllowed
        if self_multiref != other_multiref:
            return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return f"Feature(name={self.name})"

    def __repr__(self):
        return str(self)


@attr.s(slots=True, hash=False, eq=True, repr=False)
class Type:
    """Describes types in a type system.

    Instances of this class should not be created by hand, instead the type
    system's `create_type` should be used.

    """

    name: str = attr.ib()  #: Type name of this type
    supertype: "Type" = attr.ib()  # : The super type (parent) of this type
    description: str = attr.ib(default=None)  #: Description of this type
    typesystem: "TypeSystem" = attr.ib(default=None)  #: The typesystem this type belongs to
    _children: Dict[str, "Type"] = attr.ib(factory=dict)
    _features: Dict[str, Feature] = attr.ib(factory=dict)
    _inherited_features: Dict[str, Feature] = attr.ib(factory=dict)
    _constructor_fn = attr.ib(init=False, eq=False, order=False, repr=False)
    _constructor: Callable[[Dict], FeatureStructure] = attr.ib(default=None, eq=False, order=False, repr=False)
    _cached_all_features = attr.ib(default=None, eq=False, order=False, repr=False)

    def __attrs_post_init__(self):
        """Build the constructor that can create feature structures of this type"""
        name = _string_to_valid_classname(self.name)
        fields = {feature.name: attr.ib(default=None, repr=(feature.name != "sofa")) for feature in self.all_features}
        fields["type"] = attr.ib(default=self)

        # We assign this to a lambda to make it lazy
        # When creating large type systems, almost no types are used so
        # creating them on the fly is on average better
        self._constructor_fn = lambda: attr.make_class(
            name, fields, bases=(FeatureStructure,), slots=True, eq=False, order=False
        )

    def __call__(self, **kwargs) -> FeatureStructure:
        """Creates an feature structure of this type

        When called with keyword arguments whose keys are the feature names and values are the
        respective feature values, then a new feature structure instance is created.

        Returns:
            A new feature structure instance of this type.

        """
        if self._constructor is None:
            self._constructor = self._constructor_fn()

        return self._constructor(**kwargs)

    def get_feature(self, name: str) -> Optional[Feature]:
        """Find a feature by name

        This returns `None` if this type does not contain a feature
        with the given `name`.

        Args:
            name: The name of the feature

        Returns:
            The feature with name `name` or `None` if it does not exist.
        """
        if name in self._features:
            return self._features[name]
        elif name in self._inherited_features:
            return self._inherited_features[name]
        else:
            return None

    def _add_feature(self, feature: Feature, inherited: bool = False, warn: bool = True):
        """Add the given feature to his type.

        Args:
            feature: The feature
            inherited: Indicates whether this feature is inherited from a parent or not
            warn: Emit a user warning when exactly redefining features

        """
        # Clear the feature cache when adding a new feature. Note that this method is also called by supertypes when
        # a feature is added to them so that the subtypes receive the new feature as an inherited feature.
        self._cached_all_features = None
        target = self._features if not inherited else self._inherited_features

        # Check that feature is not defined in on current type
        if feature.name in target:
            redefined_feature = target[feature.name]

            if redefined_feature != feature:
                msg = "Feature with name [{}] already exists in [{}] but is redefined differently!".format(
                    feature.name, self.name
                )
                raise ValueError(msg)
            elif warn:
                msg = f"Feature with name [{feature.name}] already exists in [{self.name}]!"
                warnings.warn(msg)
            return

        # Check that feature is not redefined on parent type
        if feature.name in self._inherited_features:
            redefined_feature = self._inherited_features[feature.name]

            if redefined_feature != feature:
                msg = f"Feature with name [{feature.name}] already exists in parent but is redefined!"
                raise ValueError(msg)
            elif warn:
                msg = f"Feature with name [{feature.name}] already exists in parent!"
                warnings.warn(msg)
            return

        target[feature.name] = feature

        # Recreate constructor to incorporate new features
        self.__attrs_post_init__()

        for child_type in self._children.values():
            child_type._add_feature(feature, inherited=True)

    @property
    def features(self) -> Iterator[Feature]:
        """Returns an iterator over the features of this type. Inherited features are excluded. To
        find these in addition to this types' own features, use `all_features`.

        Returns:
            An iterator over all features of this type, excluding inherited ones

        """
        return iter(self._features.values())

    @property
    def all_features(self) -> List[Feature]:
        """Returns an iterator over the features of this type. Inherited features are included. To
        just retrieve immediate features, use `features`.

        Returns:
            An iterator over all features of this type, including inherited ones

        """

        # In particular during (de)serialization, this method is called often and it should be fast. Thus we cache
        # the vetted list of all features instead of recalculating it every time, in particular since the type system
        # should be mostly static after the initial setup
        if self._cached_all_features is None:
            # We use `unique_everseen` here, as children could redefine parent types (Issue #56)
            self._cached_all_features = list(
                unique_everseen(chain(self._features.values(), self._inherited_features.values()))
            )

        return self._cached_all_features

    @property
    def children(self) -> Iterator["Type"]:
        yield from self._children.values()

    @property
    def descendants(self) -> Iterator["Type"]:
        """
        Returns an iterator of the type and any descendant types (subtypes).
        """
        yield self
        if self._children:
            for child in self._children.values():
                yield from child.descendants

    def subsumes(self, other_type: "Type") -> bool:
        """Determines if the type `other_type` is a child of `self`.

        Args:
            other_type: Name of the type to check

        Returns:
            `True` if `self` subsumes `other_type` else `False`
        """
        if self.name == TOP_TYPE_NAME:
            return True

        cur = other_type

        while cur:
            if self.name == cur.name:
                return True
            else:
                cur = cur.supertype

        return False

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __str__(self):
        return f"Type(name={self.name})"

    def __repr__(self):
        return str(self)


class TypeSystem:
    def __init__(self, add_document_annotation_type: bool = True):
        self._types = {}

        # We store types that are predefined but still defined in the typesystem here
        # In order to restore them when serializing
        self._predefined_types = set()

        # The type system of a UIMA CAS has several predefined types. These are
        # added in the following

        # `top` is directly assigned in order to circumvent the inheritance
        top = Type(name=TOP_TYPE_NAME, supertype=None)
        self._types[top.name] = top

        # cas:NULL
        self.create_type(name="uima.cas.NULL", supertypeName="uima.cas.TOP")

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
        # FIXME "elements" is not actually a feature according to the UIMA Java SDK
        self.create_feature(t, name="elements", rangeType="uima.cas.TOP", multipleReferencesAllowed=True)

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
        self.create_feature(t, name="head", rangeType="uima.cas.TOP", multipleReferencesAllowed=True)
        self.create_feature(t, name="tail", rangeType="uima.cas.FSList", multipleReferencesAllowed=True)

        # FloatList
        self.create_type(name="uima.cas.FloatList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyFloatList", supertypeName="uima.cas.FloatList")
        t = self.create_type(name="uima.cas.NonEmptyFloatList", supertypeName="uima.cas.FloatList")
        self.create_feature(t, name="head", rangeType="uima.cas.Float")
        self.create_feature(t, name="tail", rangeType="uima.cas.FloatList", multipleReferencesAllowed=True)

        # IntegerList
        self.create_type(name="uima.cas.IntegerList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyIntegerList", supertypeName="uima.cas.IntegerList")
        t = self.create_type(name="uima.cas.NonEmptyIntegerList", supertypeName="uima.cas.IntegerList")
        self.create_feature(t, name="head", rangeType="uima.cas.Integer")
        self.create_feature(t, name="tail", rangeType="uima.cas.IntegerList", multipleReferencesAllowed=True)

        # StringList
        self.create_type(name="uima.cas.StringList", supertypeName="uima.cas.ListBase")
        self.create_type(name="uima.cas.EmptyStringList", supertypeName="uima.cas.StringList")
        t = self.create_type(name="uima.cas.NonEmptyStringList", supertypeName="uima.cas.StringList")
        self.create_feature(t, name="head", rangeType="uima.cas.String")
        self.create_feature(t, name="tail", rangeType="uima.cas.StringList", multipleReferencesAllowed=True)

        # Sofa
        t = self.create_type(name="uima.cas.Sofa", supertypeName="uima.cas.TOP")
        self.create_feature(t, name="sofaNum", rangeType="uima.cas.Integer")
        self.create_feature(t, name="sofaID", rangeType="uima.cas.String")
        self.create_feature(t, name="mimeType", rangeType="uima.cas.String")
        self.create_feature(t, name="sofaArray", rangeType="uima.cas.TOP", multipleReferencesAllowed=True)
        self.create_feature(t, name="sofaString", rangeType="uima.cas.String")
        self.create_feature(t, name="sofaURI", rangeType="uima.cas.String")

        # AnnotationBase
        t = self.create_type(name="uima.cas.AnnotationBase", supertypeName="uima.cas.TOP")
        self.create_feature(t, name="sofa", rangeType="uima.cas.Sofa")

        # Annotation
        t = self.create_type(name="uima.tcas.Annotation", supertypeName="uima.cas.AnnotationBase")
        self.create_feature(t, name="begin", rangeType="uima.cas.Integer")
        self.create_feature(t, name="end", rangeType="uima.cas.Integer")

        if add_document_annotation_type:
            self._add_document_annotation_type()

    def contains_type(self, typename: str):
        """Checks whether this type system contains a type with name `typename`.

        Args:
            typename: The name of type whose existence is to be checked.

        Returns:
            `True` if a type with `typename` exists, else `False`.
        """
        return typename in self._types

    def create_type(self, name: str, supertypeName: str = "uima.tcas.Annotation", description: str = None) -> Type:
        """Creates a new type and return it.

        Args:
            name: The name of the new type
            supertypeName: The name of the new types' supertype. Defaults to `uima.cas.AnnotationBase`
            description: The description of the new type

        Returns:
            The newly created type
        """
        if supertypeName in _INHERITANCE_FINAL_TYPES:
            raise ValueError(f"[{name}] cannot inherit from [{supertypeName}] because the latter is inheritance final")

        if self.contains_type(name) and not is_predefined(name):
            raise ValueError(f"Type with name [{name}] already exists!")

        supertype = self.get_type(supertypeName)
        new_type = Type(name=name, supertype=supertype, description=description, typesystem=self)

        if supertypeName != TOP_TYPE_NAME:
            supertype._children[name] = new_type

            for feature in supertype.all_features:
                new_type._add_feature(feature, inherited=True)

        self._types[name] = new_type
        return new_type

    def get_type(self, type_name: str) -> Type:
        """Finds a type by name in the type system of this CAS.

        Args:
            typename: The name of the type to retrieve

        Returns:
            The type with name `typename`
        Raises:
            Exception: If no type with `typename` could be found.
        """
        if self.contains_type(type_name):
            return self._types[type_name]
        else:
            raise TypeNotFoundError(f"Type with name [{type_name}] not found!")

    def get_types(self, built_in: bool = False) -> Iterator[Type]:
        """Returns all types of this type system. Normally, this excludes the built-in types

        Args:
            built_in: Also include the built-in types

        """
        if built_in:
            return self._types.values()

        return filterfalse(lambda x: x.name in _PREDEFINED_TYPES, self._types.values())

    def is_instance_of(self, type_: Union[Type, str], parent: Union[Type, str]) -> bool:
        if not parent:
            return False

        type_name = type_ if isinstance(type_, str) else type_.name
        parent_name = parent if isinstance(parent, str) else parent.name

        if type_name == parent_name:
            return True
        elif type_name == TOP_TYPE_NAME:
            return False
        else:
            super_type = self.get_type(type_).supertype if isinstance(type_, str) else type_.supertype
            parent_type = self.get_type(parent) if isinstance(parent, str) else parent
            return self.is_instance_of(super_type, parent_type)

    def is_collection(self, type_: Union[str, "Type"], feature: "Feature") -> bool:
        """Checks if the given feature for the type identified by ``type_`is a collection, e.g. list or array.

        Args:
            type_: The type to which the feature belongs (`Type` or name as string)
            feature: The feature to query for.
        Returns:
            Returns True if the given feature is a collection type, else False
        """
        return is_collection(self.get_type(type_) if isinstance(type_, str) else type_, feature)

    def is_primitive(self, type_: Union[str, Type]) -> bool:
        """Checks if the type identified by `type_name` is a primitive type.

        Args:
            type_: Type to query for (`Type` or name as string)
        Returns:
            Returns True if the type identified by `type` is a primitive type, else False
        """
        return is_primitive(self.get_type(type_) if isinstance(type_, str) else type_)

    def is_primitive_collection(self, type_: Union[str, Type]) -> bool:
        """Checks if the type identified by `type` is a primitive collection, e.g. list or array of primitives.

        Args:
            type_: Type to query for (`Type` or name as string)
        Returns:
            Returns True if the type identified by `type` is a primitive collection type, else False
        """
        return is_primitive_collection(self.get_type(type_) if isinstance(type_, str) else type_)

    def is_primitive_array(self, type_: Union[str, Type]) -> bool:
        """Checks if the type identified by `type` is a primitive array, e.g. array of primitives.

        Args:
            type_: Type to query for (`Type` or name as string)
        Returns:
            Returns `True` if the type identified by `type` is a primitive array type, else `False`
        """
        return is_primitive_array(type_)

    def is_primitive_list(self, type_: Union[str, Type]) -> bool:
        """Checks if the type identified by `type` is a primitive list, e.g. list of primitives.

        Args:
            type_: Type to query for (`Type` or name as string)
        Returns:
            Returns `True` if the type identified by `type` is a primitive array type, else `False`
        """
        return is_primitive_list(type_)

    def is_array(self, type_: Union[str, Type]) -> bool:
        """Checks if the type identified by `type` is an array.

        Args:
            type_: Type to query for (`Type` or name as string)
        Returns:
            Returns `True` if the type identified by `type` is an array type, else `False`
        """
        return is_array(type_)

    def is_list(self, type_: Union[str, Type]) -> bool:
        """Checks if the type identified by `type` is a list.

        Args:
            type_: Type to query for (`Type` or name as string)
        Returns:
            Returns `True` if the type identified by `type` is a list type, else `False`
        """
        return is_list(type_)

    def subsumes(self, parent: Union[str, Type], child: Union[str, Type]) -> bool:
        """Determines if the type `child` is a child of `parent`.

        Args:
            parent_name: Parent type (`Type` or name as string)
            child_name: Child type (`Type` or name as string)

        Returns:
            True if `parent` subsumes `child` else False
        """
        parent_type = self.get_type(parent) if isinstance(parent, str) else parent
        child_type = self.get_type(child) if isinstance(child, str) else child
        return parent_type.subsumes(child_type)

    def create_feature(
        self,
        domainType: Union[Type, str],
        name: str,
        rangeType: Union[Type, str],
        elementType: Union[Type, str] = None,
        description: str = None,
        multipleReferencesAllowed: bool = None,
    ) -> Feature:
        """Adds a feature to the given type.

        Args:
            domainType: The type to which the feature will be added
            name: The name of the new feature
            rangeType: The feature's rangeTypeName specifies the type of value that the feature can take.
            elementType: The elementType of a feature is optional, and applies only when the rangeTypeName
                is uima.cas.FSArray or uima.cas.FSList The elementType specifies what type of value can be
                assigned as an element of the array or list.
            description: The description of the new feature
            multipleReferencesAllowed: Setting this to true indicates that the array or list may be shared,
                so changes to it may affect other objects in the CAS.

        Raises:
            Exception: If a feature with name `name` already exists in `type_`.
        """
        has_reserved_name = False

        if name == "self" or name == "type":
            msg = "Trying to add feature `{0}` which is a reserved name in Python, renamed accessor to '{0}_' !".format(
                name
            )
            name = name + "_"
            has_reserved_name = True
            warnings.warn(msg)

        resolved_domain_type = self.get_type(domainType) if isinstance(domainType, str) else domainType

        feature = Feature(
            name=name,
            domainType=resolved_domain_type,
            rangeType=self.get_type(rangeType) if isinstance(rangeType, str) else rangeType,
            elementType=self.get_type(elementType) if isinstance(elementType, str) else elementType,
            description=description,
            multipleReferencesAllowed=multipleReferencesAllowed,
            has_reserved_name=has_reserved_name,
        )

        resolved_domain_type._add_feature(feature)

        return feature

    @deprecated(details="Use create_feature")
    def add_feature(
        self,
        type_: Type,
        name: str,
        rangeTypeName: str,
        elementType: str = None,
        description: str = None,
        multipleReferencesAllowed: bool = None,
    ):
        """Adds a feature to the given type.
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
        self.create_feature(type_, name, rangeTypeName, elementType, description, multipleReferencesAllowed)

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
            raise TypeError(f"`path` needs to be one of [str, None, Path], but was <{type(path)}>")

    def typecheck(self, fs: FeatureStructure) -> List[TypeCheckError]:
        """Checks whether a feature structure is type sound.

        Currently only checks `uima.cas.FSArray`.

        Args:
            fs: The feature structure to type check.

        Returns:
            List of type errors found, empty list of no errors were found.
        """
        errors = []

        t = self.get_type(fs.type.name)
        for f in t.all_features:
            if f.rangeType.name == "uima.cas.FSArray":
                feature_value = fs.value(f.name)
                if not feature_value.elements:
                    continue
                # We check for every element that it is of type `elementType` or a child thereof
                element_type = f.elementType or TOP_TYPE_NAME
                for e in feature_value.elements:
                    if not self.subsumes(element_type, e.type.name):
                        msg = "Member of [{}] has unsound type: was [{}], need [{}]!".format(
                            f.rangeType.name, e.type.name, element_type.name
                        )
                        errors.append(TypeCheckError(fs.xmiID, msg))

        return errors

    def _defines_predefined_type(self, type_name):
        self._predefined_types.add(type_name)

    def _add_document_annotation_type(self):
        t = self.create_type(name=_DOCUMENT_ANNOTATION_TYPE, supertypeName="uima.tcas.Annotation")
        self.create_feature(t, name="language", rangeType="uima.cas.String")

    def transitive_closure(self, seed_types: Set[Type], built_in: bool = False) -> Set[Type]:
        # Build transitive closure of used types by following parents, features, etc.
        transitively_referenced_types = set()
        openlist = []
        openlist.extend(seed_types)
        while openlist:
            type_ = openlist.pop(0)

            if type_ in transitively_referenced_types:
                continue

            if not built_in and type_.name in _PREDEFINED_TYPES:
                continue

            transitively_referenced_types.add(type_)

            if type_.supertype and type_.supertype not in transitively_referenced_types:
                openlist.append(type_.supertype)

            for feature in type_.all_features:
                if feature.rangeType not in transitively_referenced_types:
                    openlist.append(feature.rangeType)
                if feature.elementType and feature.elementType not in transitively_referenced_types:
                    openlist.append(feature.elementType)

        return transitively_referenced_types


# Deserializing


def load_typesystem(source: Union[IO, str, Path]) -> TypeSystem:
    """Loads a type system from a XML source.

    Args:
        source: The XML source. If `source` is a string, then it is assumed to be an XML string.
                If `source` is a file-like object, then the data is read from it.
                If `source` is a `Path`, then load the file at the given location.

    Returns:
        The deserialized type system

    """
    deserializer = TypeSystemDeserializer()
    if isinstance(source, str):
        return deserializer.deserialize(BytesIO(source.encode("utf-8")))
    elif isinstance(source, Path):
        with source.open("rb") as src:
            return deserializer.deserialize(src)
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
        type_dependencies = defaultdict(set)
        types_to_supertypes = {}

        context = etree.iterparse(source, events=("end",), tag=("{*}typeDescription",))
        for event, elem in context:
            type_name = self._get_elem_as_str(elem.find("{*}name"))
            description = self._get_elem_as_str(elem.find("{*}description"))
            supertypeName = self._get_elem_as_str(elem.find("{*}supertypeName"))

            # We store the supertype in order to later fill in the real supertype type,
            # not only the supertype name. It can be that it is a builtin or a type in
            # the type system XML is defined before its supertype.
            types_to_supertypes[type_name] = supertypeName
            types[type_name] = Type(name=type_name, supertype=None, description=description)
            type_dependencies[type_name].add(supertypeName)

            # Parse features
            for fd in elem.iterfind("{*}features/{*}featureDescription"):
                feature_name = self._get_elem_as_str(fd.find("{*}name"))
                rangeTypeName = self._get_elem_as_str(fd.find("{*}rangeTypeName"))
                description = self._get_elem_as_str(fd.find("{*}description"))
                multipleReferencesAllowed = self._get_elem_as_bool(fd.find("{*}multipleReferencesAllowed"))
                elementType = self._get_elem_as_str(fd.find("{*}elementType"))

                f = Feature(
                    domainType=type_name,  # value should actually be a Type, but we still need to load these
                    name=feature_name,
                    rangeType=rangeTypeName,  # value should actually be a Type, but we still need to load these
                    description=description,
                    multipleReferencesAllowed=multipleReferencesAllowed,
                    elementType=elementType,  # value should actually be a Type, but we still need to load these
                )
                features[type_name].append(f)

            # Free the XML tree element from memory as it is not needed anymore
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context

        ts = TypeSystem(add_document_annotation_type=False)

        # DocumentAnnotation is not a predefined UIMA type, but some applications assume that it exists.
        # It can be defined by users with custom fields. In case the loaded type system did not define
        # it, we add the standard DocumentAnnotation type. In case it is already defined, we add it to
        # the list of redefined predefined types so that is written back on serialization.
        if _DOCUMENT_ANNOTATION_TYPE not in types:
            t = Type(name=_DOCUMENT_ANNOTATION_TYPE, supertype=ts.get_type(TYPE_NAME_ANNOTATION))
            features[t.name].append(Feature(domainType=t, name="language", rangeType=TYPE_NAME_STRING))
            types[t.name] = t
            type_dependencies[t.name].add(TYPE_NAME_ANNOTATION)
        else:
            ts._defines_predefined_type(_DOCUMENT_ANNOTATION_TYPE)

        # We fill in the supertypes here now that we parsed and created all types
        for type_name, supertype_name in types_to_supertypes.items():
            t = types[type_name]

            if supertype_name in _PREDEFINED_TYPES:
                supertype = ts.get_type(supertype_name)
            else:
                supertype = types[supertype_name]

            t.supertype = supertype

        def resolve_type(type_: Union[str, Type]):
            if isinstance(type_, str):
                return ts.get_type(type_) if type_ in _PREDEFINED_TYPES else types[type_]
            return type_

        # Fill in actual types into the features
        for fl in features.values():
            for f in fl:
                f.domainType = resolve_type(f.domainType)
                f.rangeType = resolve_type(f.rangeType)
                f.elementType = resolve_type(f.elementType)

        # Some CAS handling libraries add predefined types to the typesystem XML.
        # Here we check that the redefinition of predefined types adheres to the definition in UIMA
        for type_name, t in types.items():
            if type_name in _PREDEFINED_TYPES:
                pt = ts.get_type(type_name)

                t_features = list(sorted(features[type_name]))
                pt_features = list(sorted(pt.features))

                if t.supertype != pt.supertype:
                    msg = "Redefining predefined type [{0}] with different superType [{1}], expected [{2}]"
                    raise ValueError(msg.format(type_name, t.supertype, pt.supertype))

                # We check whether the predefined type is defined the same in UIMA and this typesystem
                if t_features == pt_features:
                    # No need to create predefined types, but store them for serialization
                    ts._defines_predefined_type(type_name)
                    continue
                else:
                    msg = "Redefining predefined type [{0}] with different features: {1} - Have to be {2}"
                    raise ValueError(msg.format(type_name, t_features, pt_features))

        # Add the types to the type system in order of dependency (parents before children)
        created_types = []
        for type_name in toposort_flatten(type_dependencies, sort=False):
            # No need to recreate predefined types
            if type_name in _PREDEFINED_TYPES:
                continue

            t = types[type_name]
            created_type = ts.create_type(name=t.name, description=t.description, supertypeName=t.supertype.name)
            created_types.append(created_type)

        # Add the features to the type AFTER we create all the types to not cause circular references
        # between type references in inheritance and type references in range or element type.
        for t in created_types:
            for f in features[t.name]:
                ts.create_feature(
                    t,
                    name=f.name,
                    rangeType=f.rangeType,
                    elementType=f.elementType,
                    description=f.description,
                    multipleReferencesAllowed=f.multipleReferencesAllowed,
                )

        return ts

    def _get_elem_as_str(self, elem: etree.Element) -> Optional[str]:
        if elem is not None:
            return elem.text if elem.text is None else elem.text.strip()
        else:
            return None

    def _get_elem_as_bool(self, elem: etree.Element) -> Optional[bool]:
        if elem is not None:
            text = elem.text
            if text == "true":
                return True
            elif text == "false":
                return False
            else:
                raise ValueError("Cannot parse boolean: " + str(text))
        else:
            return None


# Serializing


class TypeSystemSerializer:
    def serialize(self, sink: Union[IO, str], typesystem: TypeSystem):
        nsmap = {None: "http://uima.apache.org/resourceSpecifier"}
        with etree.xmlfile(sink, encoding="utf-8") as xf:
            xf.write_declaration()

            with xf.element("typeSystemDescription", nsmap=nsmap):
                with xf.element("types"):
                    # In order to export the same types that we imported, we
                    # also emit the (redundant) predefined types
                    for predefined_type_name in sorted(typesystem._predefined_types):
                        predefined_type = typesystem.get_type(predefined_type_name)
                        self._serialize_type(xf, predefined_type)

                    for type_ in sorted(typesystem.get_types(), key=lambda t: t.name):
                        # We do not want to serialize our implicitly added DocumentAnnotation.
                        # If it was defined by the user, it is in `typesystem._predefined_types`
                        # and serialized in the loop before.
                        if type_.name == _DOCUMENT_ANNOTATION_TYPE:
                            continue

                        self._serialize_type(xf, type_)

    def _serialize_type(self, xf: IO, type_: Type):
        typeDescription = etree.Element("typeDescription")

        name = etree.SubElement(typeDescription, "name")
        name.text = type_.name

        description = etree.SubElement(typeDescription, "description")
        description.text = type_.description

        supertype_name_node = etree.SubElement(typeDescription, "supertypeName")
        supertype_name_node.text = type_.supertype.name

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

        feature_name = feature.name
        # If the feature name is a reserved name like `self`, then we added an
        # underscore to it before so Python can handle it. We now need to remove it.
        if feature._has_reserved_name:
            feature_name = feature_name[:-1]

        name.text = feature_name

        description = etree.SubElement(featureDescription, "description")
        description.text = feature.description

        rangeTypeName = etree.SubElement(featureDescription, "rangeTypeName")
        rangeTypeName.text = feature.rangeType.name

        if feature.multipleReferencesAllowed is not None:
            multipleReferencesAllowed = etree.SubElement(featureDescription, "multipleReferencesAllowed")
            multipleReferencesAllowed.text = "true" if feature.multipleReferencesAllowed else "false"

        if feature.elementType is not None:
            elementType = etree.SubElement(featureDescription, "elementType")
            elementType.text = feature.elementType.name


def merge_typesystems(*typesystems: TypeSystem) -> TypeSystem:
    """Merges several type systems into one.

    If a type is defined in two source file systems, then the features of all of the these types are joined together in+
    the target type system. The exact rules are outlined in
    https://uima.apache.org/d/uimaj-2.10.4/references.html#ugr.ref.cas.typemerging .

    Args:
        *typesystems: The type systems to merge

    Returns:
        A new type system that is the result of merging  all of the type systems together.
    """

    type_list = []

    for ts in typesystems:
        type_list.extend(ts.get_types())

    merged_types = set()
    merged_ts = TypeSystem()

    # A type can only be added if its supertype was added before. We therefore iterate over the list of all
    # types and remove types once we were able to merge it. If we were not able to add a type for one iteration,
    # then it means that the type systems are not mergeable and we abort with an error.
    while True:
        updated_type_list = type_list[:]
        for t in type_list:
            # Check whether the type is ready to be added
            if not is_predefined(t.supertype) and t.supertype.name not in merged_types:
                continue

            # The supertype is defined, so we can add the current type to the new type system
            if not merged_ts.contains_type(t.name):
                # Create the type and add its features as it does not exist yet in the merged type system
                created_type = merged_ts.create_type(
                    name=t.name, description=t.description, supertypeName=t.supertype.name
                )

                for feature in t.features:
                    created_type._add_feature(copy(feature), warn=False)
            else:
                # Type is already defined
                existing_type = merged_ts.get_type(t.name)

                # If the supertypes are not the same, we need to check whether they are at
                # least compatible and then patch the hierarchy
                if t.supertype.name != existing_type.supertype.name:
                    if merged_ts.subsumes(existing_type.supertype.name, t.supertype.name):
                        # Existing supertype subsumes newly specified supertype;
                        # reset supertype to the new, more specific type
                        existing_type.supertype = t.supertype
                    elif merged_ts.subsumes(t.supertype.name, existing_type.supertype.name):
                        # Newly specified supertype subsumes old type, this is OK and we don't
                        # need to do anything
                        pass
                    else:
                        msg = "Cannot merge type [{}] with incompatible super types: [{}] - [{}]".format(
                            t.name, t.supertype.name, existing_type.supertype.name
                        )
                        raise ValueError(msg)

                # If the type is already defined, merge features
                for feature in t.features:
                    existing_type._add_feature(copy(feature), warn=False)

            merged_types.add(t.name)
            updated_type_list.remove(t)

        # If there was no progress in the last iteration, then the leftover types cannot be merged
        if len(type_list) == updated_type_list:
            raise ValueError("Unmergeable types" + ", ".join([t.name for t in type_list]))

        # If there are no types to merge left, then we are done
        if len(updated_type_list) == 0:
            break

    # Fix up type references to ensure that only type instances of the merged type system are referenced, not any
    # types from the source type systems
    for t in merged_ts.get_types():
        if t.supertype:
            t.supertype = merged_ts.get_type(t.supertype.name)
        for f in t.features:
            if f.domainType:
                f.domainType = merged_ts.get_type(f.domainType.name)
            if f.rangeType:
                f.rangeType = merged_ts.get_type(f.rangeType.name)
            if f.elementType:
                f.elementType = merged_ts.get_type(f.elementType.name)
    return merged_ts


def load_dkpro_core_typesystem() -> TypeSystem:
    # https://stackoverflow.com/a/20885799
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        # Try backported to PY<37 `importlib_resources`.
        import importlib_resources as pkg_resources

    from . import resources  # relative-import the *package* containing the templates

    with pkg_resources.open_binary(resources, "dkpro-core-types.xml") as f:
        return load_typesystem(f)
