import itertools
import sys
import warnings
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

import attr
import deprecation
from attr import validators
from sortedcontainers import SortedKeyList

from cassis.typesystem import (
    FEATURE_BASE_NAME_HEAD,
    FEATURE_BASE_NAME_LANGUAGE,
    TYPE_NAME_DOCUMENT_ANNOTATION,
    TYPE_NAME_FS_ARRAY,
    TYPE_NAME_FS_LIST,
    TYPE_NAME_SOFA,
    FeatureStructure,
    Type,
    TypeCheckError,
    TypeSystem,
    TypeSystemMode,
)

_validator_optional_string = validators.optional(validators.instance_of(str))

NAME_DEFAULT_SOFA = "_InitialView"


@lru_cache(maxsize=5000)
def _get_size_in_utf16_bytes(c: str) -> int:
    return len(c.encode("utf-16-le")) // 2


class IdGenerator:
    def __init__(self, initial_id: int = 1):
        self._next_id = initial_id

    def generate_id(self) -> int:
        result = self._next_id
        self._next_id += 1
        return result


class Utf16CodepointOffsetConverter:
    """The Java platform and therefore UIMA internally uses a UTF-16 representation for text. For this reason,
    the offsets used in UIMA XMI represent offsets of the 16bit units in UTF-16 strings. We convert them internally
    to Unicode codepoints that are used by Python strings when creating a CAS. When serializing to XMI, we convert back.

    See also:
        https://webanno.github.io/webanno/releases/3.4.5/docs/user-guide.html#sect_webannotsv
        https://uima.apache.org/d/uimaj-current/references.html 4.2.1
    """

    def __init__(self):
        self._external_to_python: Union[Dict[int, int], None] = None
        self._python_to_external: Union[Dict[int, int], None] = None

    def create_offset_mapping(self, sofa_string: str) -> None:
        if sofa_string is None:
            return

        sizes_in_utf16_bytes = map(_get_size_in_utf16_bytes, sofa_string)
        accumulated_sizes = [0] + list(itertools.accumulate(sizes_in_utf16_bytes))

        self._python_to_external = dict(zip(range(len(accumulated_sizes)), accumulated_sizes))
        self._external_to_python = dict(zip(accumulated_sizes, range(len(accumulated_sizes))))

    def external_to_python(self, idx: Optional[int]) -> Optional[int]:
        if idx is None:
            return None

        if self._external_to_python is None:
            return idx

        try:
            return self._external_to_python[idx]
        except KeyError:
            warnings.warn(
                f"Not mapping external offset [{idx}] which is not valid within the internal range [0-{list(self._external_to_python)[-1]}]"
            )
            return idx

    def python_to_external(self, idx: Optional[int]) -> Optional[int]:
        if idx is None:
            return None

        if self._python_to_external is None:
            return idx

        try:
            return self._python_to_external[idx]
        except KeyError:
            warnings.warn(
                f"Not mapping internal offset [{idx}] which is not valid within the external range [0-{list(self._python_to_external)[-1]}]"
            )
            return idx


@attr.s(slots=True)
class Sofa:
    """Each CAS has one or more Subject of Analysis (SofA)"""

    #: "Type": The type
    type = attr.ib(repr=False)

    #: int: The sofaNum
    sofaNum = attr.ib(validator=validators.instance_of(int))

    #: int: The XMI id
    xmiID = attr.ib(validator=validators.instance_of(int))

    #: str: The name of the sofa, i.e. the sofa ID
    sofaID = attr.ib(validator=validators.instance_of(str))

    #: str: The text corresponding to this sofa
    _sofaString = attr.ib(default=None, validator=_validator_optional_string)

    #: str: The mime type of `sofaString`
    mimeType = attr.ib(default=None, validator=_validator_optional_string)

    #: str: The sofa URI, it references remote sofa data
    sofaURI = attr.ib(default=None, validator=_validator_optional_string)

    #: str: The sofa data byte array
    sofaArray = attr.ib(default=None)

    #: Utf16CodepointOffsetConverter: Converts from UIMA UTF-16 based offsets to Unicode codepoint offsets and back
    _offset_converter = attr.ib(factory=Utf16CodepointOffsetConverter, eq=False, hash=False, repr=False)

    @property
    def sofaString(self) -> str:
        return self._sofaString

    @sofaString.setter
    def sofaString(self, value: str):
        self._sofaString = value
        self._offset_converter.create_offset_mapping(value)

    def __attrs_post_init__(self):
        if self._sofaString:
            self._offset_converter.create_offset_mapping(self._sofaString)


class View:
    """A view into a CAS contains a subset of feature structures and annotations."""

    def __init__(self, sofa: Sofa):
        """Creates a new view for the given sofa.

        Args:
            sofa: The sofa associated with this view.
        """
        self.sofa = sofa

        # Annotations are sorted by begin index first (smaller first). If begin
        # is equal, sort by end index, smaller first. This is the same as
        # comparing a Python tuple of (begin, end)
        self._indices = defaultdict(lambda: SortedKeyList(key=_sort_func))

    @property
    def type_index(self) -> Dict[str, SortedKeyList]:
        """Returns an index mapping type names to annotations of this type.

        Returns:
            A dictionary mapping type names to annotations of this type.
        """
        return self._indices

    def add_annotation_to_index(self, annotation: FeatureStructure):
        self._indices[annotation.type.name].add(annotation)

    def get_all_annotations(self) -> List[FeatureStructure]:
        """Gets all the annotations in this view.

        Returns:
            A list of all annotations in this view.

        """
        result = []
        for annotations_by_type in self._indices.values():
            result.extend(annotations_by_type)
        return result

    def remove_annotation_from_index(self, annotation: FeatureStructure):
        """Removes an annotation from an index. This throws if the
        annotation was not present.

        Args:
            annotation: The annotation to remove.
        """
        self._indices[annotation.type.name].remove(annotation)


class Index:
    def __init__(self, typesystem: TypeSystem):
        self._data = SortedKeyList(key=_sort_func)
        self._typesystem = typesystem


class Cas:
    """A CAS object is a container for text (sofa) and annotations"""

    def __init__(
        self,
        typesystem: TypeSystem = None,
        lenient: bool = False,
        sofa_string: str = None,
        sofa_mime: str = None,
        document_language: str = None,
    ):
        """Creates a CAS with the specified typesystem. If no typesystem is given, then the default one
        is used which only contains UIMA-predefined types.

        Args:
            typesystem: The types system to use.
        """
        self._typesystem = typesystem if typesystem else TypeSystem()
        self._lenient = lenient

        # When new attributes are added, they also need to be added in Cas::_copy. The copying
        # relies on the fact that all the members of the Cas are mutable references. It is not
        # possible right now to add not-mutable references because the view functionality heavily
        # relies on this functionality.
        self._sofas = {}
        self._views = {}

        self._xmi_id_generator = IdGenerator()
        self._sofa_num_generator = IdGenerator()

        # Every CAS comes with a an initial view called `_InitialView`
        self._add_view("_InitialView")
        self._current_view: View = self._views["_InitialView"]

        if sofa_string is not None:
            self.sofa_string = sofa_string
            if sofa_mime is not None:
                self.sofa_mime = sofa_mime
            else:
                self.sofa_mime = "text/plain"

        if document_language is not None:
            self.document_language = document_language

    @property
    def typesystem(self) -> TypeSystem:
        return self._typesystem

    def create_view(self, name: str, xmiID: Optional[int] = None, sofaNum: Optional[int] = None) -> "Cas":
        """Create a view and its underlying Sofa (subject of analysis).

        Args:
            name: The name of the view. This is the same as the associated Sofa name.
            xmiID: If specified, use this XMI id instead of generating a new one.
            sofaNum: If specified, use this sofaNum instead of generating a new one.

        Returns:
            The newly created view.

        Raises:
            ValueError: If a view with `name` already exists.
        """
        if name in self._views:
            raise ValueError(f"A view with name [{name}] already exists!")

        self._add_view(name, xmiID=xmiID, sofaNum=sofaNum)
        return self.get_view(name)

    def _add_view(self, name: str, xmiID: Optional[int] = None, sofaNum: Optional[int] = None):
        if xmiID is None:
            xmiID = self._get_next_xmi_id()

        if sofaNum is None:
            sofaNum = self._get_next_sofa_num()

        # Create sofa
        sofa = Sofa(xmiID=xmiID, sofaNum=sofaNum, sofaID=name, type=self.typesystem.get_type(TYPE_NAME_SOFA))

        # Create view
        view = View(sofa=sofa)

        self._views[name] = view
        self._sofas[name] = sofa

    def get_view(self, name: str) -> "Cas":
        """Gets an existing view.

        Args:
            name: The name of the view. This is the same as the associated Sofa name.

        Returns:
            The view corresponding to `name`
        """
        if name in self._views:
            # Make a shallow copy of this CAS and just change the current view.
            result = self._copy()
            result._current_view = self._views[name]
            return result
        else:
            raise KeyError(f"There is no view with name [{name}] in this CAS!")

    @property
    def views(self) -> List[View]:
        """Finds all views that this CAS manages.

        Returns:
            The list of all views belonging to this CAS.

        """
        return list(self._views.values())

    def add(self, annotation: FeatureStructure, keep_id: Optional[bool] = True):
        """Adds an annotation to this Cas.

        Args:
            annotation: The annotation to add.
            keep_id: Keep the XMI id of `annotation` if true, else generate a new one.

        """
        if not self._lenient and not self._typesystem.contains_type(annotation.type.name):
            msg = f"Typesystem of CAS does not contain type [{annotation.type.name}]. "
            msg += "Either add the type to the type system or specify `lenient=True` when creating the CAS."
            raise RuntimeError(msg)

        if keep_id and annotation.xmiID is not None:
            next_id = annotation.xmiID
        else:
            next_id = self._get_next_xmi_id()

        annotation.xmiID = next_id
        if hasattr(annotation, "sofa"):
            annotation.sofa = self.get_sofa()

        self._current_view.add_annotation_to_index(annotation)

    @deprecation.deprecated(details="Use add()")
    def add_annotation(self, annotation: FeatureStructure, keep_id: Optional[bool] = True):
        """Adds an annotation to this Cas.

        Args:
            annotation: The annotation to add.
            keep_id: Keep the XMI id of `annotation` if true, else generate a new one.

        """
        self.add(annotation, keep_id)

    def add_all(self, annotations: Iterable[FeatureStructure]):
        """Adds several annotations at once to this CAS.

        Args:
            annotations: An iterable of annotations to add.

        """
        for annotation in annotations:
            self.add(annotation)

    @deprecation.deprecated(details="Use add_all()")
    def add_annotations(self, annotations: Iterable[FeatureStructure]):
        """Adds several annotations at once to this CAS.

        Args:
            annotations: An iterable of annotations to add.

        """
        self.add_all(annotations)

    def remove(self, annotation: FeatureStructure):
        """Removes an annotation from an index. This throws if the
        annotation was not present.

        Args:
            annotation: The annotation to remove.
        """
        self._current_view.remove_annotation_from_index(annotation)

    @deprecation.deprecated(details="Use remove()")
    def remove_annotation(self, annotation: FeatureStructure):
        """Removes an annotation from an index. This throws if the
        annotation was not present.

        Args:
            annotation: The annotation to remove.
        """
        self.remove(annotation)

    @deprecation.deprecated(details="Use annotation.get_covered_text()")
    def get_covered_text(self, annotation: FeatureStructure) -> str:
        """Gets the text that is covered by `annotation`.

        Args:
            annotation: The annotation whose covered text is to be retrieved.

        Returns:
            The text covered by `annotation`

        """
        sofa = self.get_sofa()
        return sofa.sofaString[annotation.begin : annotation.end]

    def select(self, type_: Union[Type, str]) -> List[FeatureStructure]:
        """Finds all annotations of type `type_name`.

        Args:
            type_: The type or name of the type name whose annotation instances are to be found

        Returns:
            A list of all feature structures of type `type_name`

        """
        t = type_ if isinstance(type_, Type) else self.typesystem.get_type(type_)
        return self._get_feature_structures(t)

    def select_covered(self, type_: Union[Type, str], covering_annotation: FeatureStructure) -> List[FeatureStructure]:
        """Returns a list of covered annotations.

        Return all annotations that are covered

        Only returns annotations that are fully covered, overlapping annotations
        are ignored.

        Args:
            type_: The type or name of the type name whose annotation instances are to be found
            covering_annotation: The name of the annotation which covers

        Returns:
            A list of covered annotations

        """
        t = type_ if isinstance(type_, Type) else self.typesystem.get_type(type_)
        c_begin = covering_annotation.begin
        c_end = covering_annotation.end

        result = []
        for annotation in self._get_feature_structures_in_range(t, c_begin, c_end):
            if annotation.begin >= c_begin and annotation.end <= c_end:
                result.append(annotation)
        return result

    def select_covering(self, type_: Union[Type, str], covered_annotation: FeatureStructure) -> List[FeatureStructure]:
        """Returns a list of annotations that cover the given annotation.

        Return all annotations that are covering. This can be potentially be slow.

        Only returns annotations that are fully covering, overlapping annotations
        are ignored.

        Args:
            type_: The type or name of the type name whose annotation instances are to be found
            covered_annotation: The name of the annotation which is covered

        Returns:
            A list of covering annotations

        """
        t = type_ if isinstance(type_, Type) else self.typesystem.get_type(type_)
        c_begin = covered_annotation.begin
        c_end = covered_annotation.end

        # We iterate over all annotations and check whether the provided annotation
        # is covered in the current annotation
        for annotation in self._get_feature_structures(t):
            if c_begin >= annotation.begin and c_end <= annotation.end:
                yield annotation

    def select_all(self) -> List[FeatureStructure]:
        """Finds all feature structures in this Cas

        Returns:
            A list of all annotations in this Cas

        """
        return self._current_view.get_all_annotations()

    # FS handling

    def _get_feature_structures(self, type_: Type) -> List[FeatureStructure]:
        """Returns a list of all feature structures of type `type_name` and child types."""
        types = {c.name for c in type_.descendants}

        result = []
        for name in types:
            result.extend(self._current_view.type_index[name])

        return result

    def _get_feature_structures_in_range(self, type_: Type, begin: int, end: int) -> List[FeatureStructure]:
        """Returns a list of all feature structures of type `type_name` and child types.
        Only features are returned that are in [begin, end] or close to it. If you use this function,
        you should always check bound in the calling method.
        """
        types = {c.name for c in type_.descendants}

        result = []
        for name in types:
            annotations = self._current_view.type_index[name]

            # We use binary search to find indices for the first and last annotations that are inside
            # the window of [begin, end].
            idx_begin = annotations.bisect_key_left((begin, begin))
            idx_end = annotations.bisect_key_right((end, end))

            result.extend(annotations[idx_begin:idx_end])

        return result

    # Sofa

    def get_sofa(self) -> Sofa:
        """Get the Sofa feature structure associated with this CAS view.

        Returns:
            The sofa associated with this CAS view.
        """
        return self._current_view.sofa

    def get_document_annotation(self) -> FeatureStructure:
        """Get the DocumentAnnotation feature structure associated with this CAS view. If none exists, one is created.

        Returns:
            The DocumentAnnotation associated with this CAS view.
        """
        try:
            return self.select(TYPE_NAME_DOCUMENT_ANNOTATION)[0]
        except IndexError:
            document_annotation = self.typesystem.get_type(TYPE_NAME_DOCUMENT_ANNOTATION)()
            self.add(document_annotation)
            return document_annotation

    @property
    def sofas(self) -> List[Sofa]:
        """Finds all sofas that this CAS manages

        Returns:
            The list of all sofas belonging to this CAS

        """
        return list(self._sofas.values())

    @property
    def sofa_string(self) -> str:
        """The sofa string contains the document text.

        Returns: The sofa string.

        """
        return self.get_sofa().sofaString

    @sofa_string.setter
    def sofa_string(self, value: str):
        """Sets the sofa string to `value`.

        Args:
            value: The new sofa string.

        """
        self.get_sofa().sofaString = value

    @property
    def sofa_mime(self) -> str:
        """The sofa mime contains the MIME type of the document text.

        Returns: The sofa MIME type.

        """
        return self.get_sofa().mimeType

    @sofa_mime.setter
    def sofa_mime(self, value: str):
        """Sets the sofa MIME type to `value`.

        Args:
            value: The new sofa MIME type.

        """
        self.get_sofa().mimeType = value

    @property
    def sofa_uri(self) -> str:
        """The sofa URI references external sofa data.

        Returns: The sofa URI.

        """
        return self.get_sofa().sofaURI

    @sofa_uri.setter
    def sofa_uri(self, value: str):
        """Sets the sofa URI to `value`.

        Args:
            value: The new sofa URI.

        """
        self.get_sofa().sofaURI = value

    @property
    def sofa_array(self) -> str:
        """The sofa byte array references a uima.cas.ByteArray feature structure

        Returns: The sofa data byte array.

        """
        return self.get_sofa().sofaArray

    @sofa_array.setter
    def sofa_array(self, value):
        """Sets the sofa byte array to the given uima.cas.ByteArray feature structure.

        Args:
            value: The new sofa byte array feature structure.

        """
        self.get_sofa().sofaArray = value

    @property
    def document_language(self) -> str:
        """The document language contains the language code for the document.

        Returns: The document language.

        """
        return self.get_document_annotation().get(FEATURE_BASE_NAME_LANGUAGE)

    @document_language.setter
    def document_language(self, value) -> str:
        """Sets document language.

        Args:
            value: The document language
        """
        self.get_document_annotation().set(FEATURE_BASE_NAME_LANGUAGE, value)

    def to_xmi(self, path: Union[str, Path, None] = None, pretty_print: bool = False) -> Optional[str]:
        """Creates a XMI representation of this CAS.

        Args:
            path: File path, if `None` is provided the result is returned as a string
            pretty_print: `True` if the resulting XML should be pretty-printed, else `False`


        Returns:
            If `path` is None, then the XMI representation of this CAS is returned as a string

        """
        from cassis.xmi import CasXmiSerializer

        return self._serialize(CasXmiSerializer(), path, pretty_print=pretty_print)

    def to_json(
        self,
        path: Union[str, Path, None] = None,
        pretty_print: bool = False,
        ensure_ascii=False,
        type_system_mode: TypeSystemMode = TypeSystemMode.FULL,
    ) -> Optional[str]:
        """Creates a JSON representation of this CAS.

        Args:
            path: File path, if `None` is provided the result is returned as a string
            pretty_print: `True` if the resulting JSON should be pretty-printed, else `False`
            ensure_ascii: Whether to escape non-ASCII Unicode characters or not
            type_system_mode: Whether to serialize the full type system (`FUL`), only the types used (`MINIMAL`), or no
                              type system information at all (`NONE`)

        Returns:
            If `path` is None, then the JSON representation of this CAS is returned as a string
        """
        from cassis.json import CasJsonSerializer

        return self._serialize(
            CasJsonSerializer(),
            path,
            pretty_print=pretty_print,
            ensure_ascii=ensure_ascii,
            type_system_mode=type_system_mode,
        )

    def _serialize(self, serializer, path: Union[str, Path, None] = None, **kwargs):
        """Runs this CAS through the given serializer.

        Args:
            path: File path, if `None` is provided the result is returned as a string


        Returns:
            If `path` is None, then the data representation of this CAS is returned as a string

        """
        # If `path` is None, then serialize to a string and return it
        if path is None:
            return serializer.serialize(None, self, **kwargs)
        elif isinstance(path, str):
            with open(path, "wb") as f:
                serializer.serialize(f, self, **kwargs)
        elif isinstance(path, Path):
            with path.open("wb") as f:
                serializer.serialize(f, self, **kwargs)
        else:
            raise TypeError(f"`path` needs to be one of [str, None, Path], but was <{type(path)}>")

    def typecheck(self) -> List[TypeCheckError]:
        """Checks whether all feature structures in this CAS are type sound.

        For more information, see `cassis.TypesSystem::typecheck`.

        Returns:
            List of type errors found, empty list of no errors were found.
        """
        all_errors = []
        for fs in self._find_all_fs():
            errors = self.typesystem.typecheck(fs)
            all_errors.extend(errors)

        return all_errors

    def _find_all_fs(
        self,
        generate_missing_ids: bool = True,
        include_inlinable_arrays_and_lists: bool = False,
        seeds: Iterable = None,
    ) -> Iterable[FeatureStructure]:
        """This function traverses the whole CAS in order to find all directly and indirectly referenced
        feature structures. Traversing is needed as it can be that a feature structure is not added to the sofa but
        referenced by another feature structure as a feature."""
        all_fs = {}

        openlist = []
        if seeds is not None:  # Using "is not None" to distinguish empty seeds from not using seeds at all
            openlist.extend(seeds)
        else:
            for sofa in self.sofas:
                view = self.get_view(sofa.sofaID)
                openlist.extend(view.select_all())

        ts = self.typesystem
        while openlist:
            fs = openlist.pop(0)

            # We do not want to return cas:NULL here as we handle serializing it later
            if fs.xmiID == 0:
                continue

            if fs.xmiID is None:
                if generate_missing_ids:
                    fs.xmiID = self._get_next_xmi_id()
                else:
                    raise ValueError(f"FS has no ID and ID generation is disabled! {fs}")

            existing_fs = all_fs.get(fs.xmiID)
            if existing_fs is not None and existing_fs is not fs:
                raise ValueError(
                    "Duplicate FS id [{fsId}] used for [{fs1}] and [{fs2}]".format(
                        fsId=fs.xmiID, fs1=existing_fs, fs2=fs
                    )
                )

            all_fs[fs.xmiID] = fs

            t = ts.get_type(fs.type.name)

            # Arrays contents are handled separately - they only have one "virtual" feature: elements
            if t.supertype.name == "uima.cas.ArrayBase":
                if t.name == "uima.cas.FSArray" and fs.elements:
                    for ref in fs.elements:
                        if not ref or ref.xmiID in all_fs:
                            continue
                        openlist.append(ref)
                continue  # After processing any arrays, skip to the next FS in the openlist

            # For non-array types, we look at the features - this includes also FSList-types
            for feature in t.all_features:
                feature_name = feature.name

                if feature_name == "sofa":
                    continue

                if ts.is_primitive(feature.rangeType):
                    continue

                feature_value = getattr(fs, feature_name)
                if feature_value is None:
                    continue

                if (
                    not include_inlinable_arrays_and_lists
                    and not feature.multipleReferencesAllowed
                    and (ts.is_array(feature.rangeType) or ts.is_list(feature.rangeType))
                ):
                    # For inlined FSArrays / FSList, we still need to scan their members
                    if feature.rangeType.name == TYPE_NAME_FS_ARRAY and feature_value.elements:
                        for ref in feature_value.elements:
                            if not ref or ref.xmiID in all_fs:
                                continue
                            openlist.append(ref)
                    elif feature.rangeType.name == TYPE_NAME_FS_LIST and hasattr(feature_value, FEATURE_BASE_NAME_HEAD):
                        v = feature_value
                        while hasattr(v, FEATURE_BASE_NAME_HEAD):
                            if not v.head or v.head.xmiID in all_fs:
                                continue
                            openlist.append(v.head)
                            v = v.tail
                    # For primitive arrays / lists, we do not need to handle the elements
                    continue

                if not hasattr(feature_value, "xmiID"):
                    raise AttributeError(
                        f"Feature [{feature.domainType.name}:{feature_name}] should point to a [{feature.rangeType.name}] but the feature value is a [{type(feature_value)}] with the value [{feature_value}]"
                    )

                if feature_value.xmiID in all_fs:
                    continue

                openlist.append(feature_value)

        yield from all_fs.values()

    def _get_next_xmi_id(self) -> int:
        return self._xmi_id_generator.generate_id()

    def _get_next_sofa_num(self) -> int:
        return self._sofa_num_generator.generate_id()

    def _copy(self) -> "Cas":
        result = Cas(self._typesystem)
        result._views = self._views
        result._sofas = self._sofas
        result._current_view = self._current_view
        result._sofa_num_generator = self._sofa_num_generator
        result._xmi_id_generator = self._xmi_id_generator
        return result


def _sort_func(a: FeatureStructure) -> Tuple[int, int, int]:
    d = a.__slots__
    if "begin" in d and "end" in d:
        return a.begin, a.end, id(a)
    else:
        return sys.maxsize, sys.maxsize, id(a)
