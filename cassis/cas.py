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
    TYPE_NAME_ANNOTATION,
    TYPE_NAME_ARRAY_BASE,
    TYPE_NAME_DOCUMENT_ANNOTATION,
    TYPE_NAME_EMPTY_FLOAT_LIST,
    TYPE_NAME_EMPTY_INTEGER_LIST,
    TYPE_NAME_EMPTY_STRING_LIST,
    TYPE_NAME_FLOAT_LIST,
    TYPE_NAME_FS_ARRAY,
    TYPE_NAME_FS_LIST,
    TYPE_NAME_INTEGER_LIST,
    TYPE_NAME_NON_EMPTY_FLOAT_LIST,
    TYPE_NAME_NON_EMPTY_INTEGER_LIST,
    TYPE_NAME_NON_EMPTY_STRING_LIST,
    TYPE_NAME_SOFA,
    TYPE_NAME_STRING_LIST,
    FeatureStructure,
    Annotation,
    Type,
    TypeCheckError,
    TypeNotFoundError,
    TypeSystem,
    TypeSystemMode,
    is_annotation,
    load_typesystem,
)

_PRIMITIVE_LIST_BASE_TYPE = {
    TYPE_NAME_INTEGER_LIST: TYPE_NAME_INTEGER_LIST,
    TYPE_NAME_EMPTY_INTEGER_LIST: TYPE_NAME_INTEGER_LIST,
    TYPE_NAME_NON_EMPTY_INTEGER_LIST: TYPE_NAME_INTEGER_LIST,
    TYPE_NAME_FLOAT_LIST: TYPE_NAME_FLOAT_LIST,
    TYPE_NAME_EMPTY_FLOAT_LIST: TYPE_NAME_FLOAT_LIST,
    TYPE_NAME_NON_EMPTY_FLOAT_LIST: TYPE_NAME_FLOAT_LIST,
    TYPE_NAME_STRING_LIST: TYPE_NAME_STRING_LIST,
    TYPE_NAME_EMPTY_STRING_LIST: TYPE_NAME_STRING_LIST,
    TYPE_NAME_NON_EMPTY_STRING_LIST: TYPE_NAME_STRING_LIST,
}

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

    def add_fs_to_indexes(self, fs: FeatureStructure):
        """Adds a feature structure to the indexes of this view."""
        self._indices[fs.type.name].add(fs)

    @deprecation.deprecated(details="Use add_fs_to_indexes()")
    def add_annotation_to_index(self, annotation: FeatureStructure):
        """Adds a feature structure to the indexes of this view.

        .. deprecated::
            Use :meth:`add_fs_to_indexes`.
        """
        self.add_fs_to_indexes(annotation)

    def get_all_fs(self) -> List[FeatureStructure]:
        """Gets all indexed feature structures in this view.

        Returns:
            A list of all indexed feature structures (annotations and non-annotations) in this view.

        """
        result = []
        for fs_by_type in self._indices.values():
            result.extend(fs_by_type)
        return result

    @deprecation.deprecated(details="Use get_all_fs() for all indexed feature structures or filter with cassis.typesystem.is_annotation")
    def get_all_annotations(self) -> List[FeatureStructure]:
        """Gets all indexed annotations in this view.

        .. deprecated::
            Use :meth:`get_all_fs` for all indexed feature structures, or filter the result
            with :func:`cassis.typesystem.is_annotation`.
        """
        return [fs for fs in self.get_all_fs() if is_annotation(fs)]

    def remove_fs_from_indexes(self, fs: FeatureStructure):
        """Removes a feature structure from the indexes of this view. Throws if the
        feature structure was not present.

        Args:
            fs: The feature structure to remove.
        """
        self._indices[fs.type.name].remove(fs)

    @deprecation.deprecated(details="Use remove_fs_from_indexes()")
    def remove_annotation_from_index(self, annotation: FeatureStructure):
        """Removes a feature structure from the indexes of this view. Throws if the
        feature structure was not present.

        .. deprecated::
            Use :meth:`remove_fs_from_indexes`.
        """
        self.remove_fs_from_indexes(annotation)


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
        sofa_string: Optional[str] = None,
        sofa_mime: Optional[str] = None,
        document_language: Optional[str] = None,
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
        self._views: dict[str, View] = {}

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

    def add(self, fs: FeatureStructure, keep_id: Optional[bool] = True):
        """Adds a feature structure to this Cas.

        Args:
            fs: The feature structure to add.
            keep_id: Keep the XMI id of `fs` if true, else generate a new one.

        """
        if not self._lenient and not self._typesystem.contains_type(fs.type.name):
            msg = f"Typesystem of CAS does not contain type [{fs.type.name}]. "
            msg += "Either add the type to the type system or specify `lenient=True` when creating the CAS."
            raise RuntimeError(msg)

        if keep_id and fs.xmiID is not None:
            next_id = fs.xmiID
        else:
            next_id = self._get_next_xmi_id()

        fs.xmiID = next_id
        if hasattr(fs, "sofa"):
            fs.sofa = self.get_sofa()

        self._current_view.add_fs_to_indexes(fs)

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

    def crop_sofa_string(self, sofa_begin: int, sofa_end: int, overlap: bool = True):
        """Replaces current sofa string with a cutout of the given range. Removes all annotations outside of range,
        but keeps annotations that overlap with cutout points by default.

        Args:
            sofa_begin: The beginning of the cutout sofa.
            sofa_end: The end of the cutout sofa.
            overlap: If true, keeps overlapping annotations and modifies begin and end of annotation accordingly.

        Raises:
            ValueError: If cutout indices are invalid.
        Note:
            Removal performed by this method only removes annotations from the current view's
            index. Feature structures that are removed from the view remain in memory and any
            references from kept annotations to those feature structures are left intact. Such
            transitively referenced feature structures will still be discovered by traversal
            (e.g. ``_find_all_fs()``) and included during serialization.

            Important: only the annotations that are kept (inside the cut or overlapping
            the cut boundaries) have their ``begin``/``end`` offsets adjusted to the new
            sofa coordinate space. Feature structures that are removed from the view are
            not re-anchored or relocated — they keep their original ``begin``/``end``
            values. As a result, serializers may attempt to transcode offsets that fall
            outside the new sofa range; the offset converter will emit ``UserWarning``
            messages for unmappable offsets but will not raise an exception. If you
            require a cascading delete or re-anchoring of transitively referenced feature
            structures, perform an explicit graph traversal and removal or implement an
            opt-in ``cascade=True`` behavior.
        """
        if self.sofa_string is None:
            raise ValueError("Cannot crop sofa string: CAS has no sofa string for the current view")

        if 0 <= sofa_begin < sofa_end <= len(self.sofa_string):
            self.sofa_string = self.sofa_string[sofa_begin:sofa_end]
            # Make an explicit snapshot of the current annotations to avoid
            # issues when removing/modifying elements during iteration.
            for annotation in list(self.select_all_annotations()):
                # Determine whether the annotation will be kept and how its
                # offsets need to be adjusted. If offsets are adjusted we must
                # reindex the annotation (remove then add) so that the
                # underlying SortedKeyList remains correctly ordered by the
                # updated begin/end values.
                if sofa_begin <= annotation.begin and annotation.end <= sofa_end:
                    # fully contained
                    self._current_view.remove_fs_from_indexes(annotation)
                    annotation.begin = annotation.begin - sofa_begin
                    annotation.end = annotation.end - sofa_begin
                    self._current_view.add_fs_to_indexes(annotation)
                elif overlap and sofa_begin < annotation.end <= sofa_end:
                    # left overlap (annotation starts before cut)
                    self._current_view.remove_fs_from_indexes(annotation)
                    annotation.begin = 0
                    annotation.end = annotation.end - sofa_begin
                    self._current_view.add_fs_to_indexes(annotation)
                elif overlap and sofa_begin <= annotation.begin < sofa_end:
                    # right overlap (annotation ends after cut)
                    self._current_view.remove_fs_from_indexes(annotation)
                    annotation.begin = annotation.begin - sofa_begin
                    annotation.end = len(self.sofa_string)
                    self._current_view.add_fs_to_indexes(annotation)
                elif overlap and annotation.begin <= sofa_begin and sofa_end <= annotation.end:
                    # annotation fully covers the cut
                    self._current_view.remove_fs_from_indexes(annotation)
                    annotation.begin = 0
                    annotation.end = len(self.sofa_string)
                    self._current_view.add_fs_to_indexes(annotation)
                else:
                    # annotation falls completely outside the cut; remove it
                    self.remove(annotation)
        else:
            raise ValueError(f"Invalid indices for begin {sofa_begin} and end {sofa_end}")

    def remove(self, annotation: FeatureStructure):
        """Removes an annotation from an index. This throws if the
        annotation was not present.

        Args:
            annotation: The annotation to remove.
        """
        self._current_view.remove_fs_from_indexes(annotation)

    @deprecation.deprecated(details="Use remove()")
    def remove_annotation(self, annotation: FeatureStructure):
        """Removes an annotation from an index. This throws if the
        annotation was not present.

        Args:
            annotation: The annotation to remove.
        """
        self.remove(annotation)

    def remove_annotations_in_range(self, begin: int, end: int, type_: Optional[Union[Type, str]] = None):
        """Removes annotations between two indices of the sofa string.

        Args:
            begin: The beginning of the cutting interval.
            end: The end of the cutting interval.
            type_: The type or name of the type name whose annotation instances are to be found
        Raises:
            ValueError: If range indices are invalid.
            TypeError: If ``type_`` is not a subtype of ``uima.tcas.Annotation``.
        """

        if type_ is None:
            annotations = self.select_all_annotations()
        else:
            annotations = self.select(self._require_annotation_type(type_, "remove_annotations_in_range"))
        if self.sofa_string is None:
            raise ValueError("Cannot remove annotations by range: CAS has no sofa string for the current view")

        if 0 <= begin < end <= len(self.sofa_string):
            # Make an explicit snapshot of the annotations to avoid issues when
            # removing elements during iteration (defensive copy).
            for annotation in list(annotations):
                if begin <= annotation.begin < annotation.end <= end:
                    self.remove(annotation)
        else:
            raise ValueError(f"Invalid indices for begin {begin} and end {end}")

    @deprecation.deprecated(details="Use annotation.get_covered_text()")
    def get_covered_text(self, annotation: Annotation) -> str:
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

    def select_covered(self, type_: Union[Type, str], covering_annotation: Annotation) -> List[Annotation]:
        """Returns a list of covered annotations.

        Return all annotations that are covered

        Only returns annotations that are fully covered, overlapping annotations
        are ignored.

        Args:
            type_: The type or name of the type name whose annotation instances are to be found
            covering_annotation: The name of the annotation which covers

        Returns:
            A list of covered annotations

        Raises:
            TypeError: If ``type_`` is not a subtype of ``uima.tcas.Annotation``.

        """
        t = self._require_annotation_type(type_, "select_covered")
        c_begin = covering_annotation.begin
        c_end = covering_annotation.end

        result = []
        for annotation in self._get_feature_structures_in_range(t, c_begin, c_end):
            if annotation.begin >= c_begin and annotation.end <= c_end:
                result.append(annotation)
        return result

    def select_covering(self, type_: Union[Type, str], covered_annotation: Annotation) -> List[Annotation]:
        """Returns a list of annotations that cover the given annotation.

        Return all annotations that are covering. This can be potentially be slow.

        Only returns annotations that are fully covering, overlapping annotations
        are ignored.

        Args:
            type_: The type or name of the type name whose annotation instances are to be found
            covered_annotation: The name of the annotation which is covered

        Returns:
            A list of covering annotations

        Raises:
            TypeError: If ``type_`` is not a subtype of ``uima.tcas.Annotation``.

        """
        t = self._require_annotation_type(type_, "select_covering")
        c_begin = covered_annotation.begin
        c_end = covered_annotation.end

        result = []
        for annotation in self._get_feature_structures(t):
            if c_begin >= annotation.begin and c_end <= annotation.end:
                result.append(annotation)
        return result

    def select_all_fs(self) -> List[FeatureStructure]:
        """Returns all indexed feature structures (annotations and non-annotations) in the current view.

        Returns:
            A list of all indexed feature structures in the current view.
        """
        return self._current_view.get_all_fs()

    def select_all_annotations(self) -> List[Annotation]:
        """Returns all indexed annotations in the current view.

        Non-annotation feature structures present in the view are filtered out, so it is safe
        to access ``begin``/``end`` on the returned items.

        Returns:
            A list of all indexed annotations in the current view.
        """
        return [fs for fs in self._current_view.get_all_fs() if is_annotation(fs)]

    @deprecation.deprecated(details="Use select_all_annotations() for annotations only or select_all_fs() for all indexed feature structures")
    def select_all(self) -> List[Annotation]:
        """Finds all annotations in this Cas.

        .. deprecated::
            Use :meth:`select_all_annotations` for annotations only, or
            :meth:`select_all_fs` for all indexed feature structures.
        """
        return self.select_all_annotations()

    # FS handling

    def _require_annotation_type(self, type_: Union[Type, str], operation: str) -> Type:
        """Resolves ``type_`` and validates it is a subtype of ``uima.tcas.Annotation``.

        Raises:
            TypeError: If the resolved type is not an annotation type.
        """
        t = type_ if isinstance(type_, Type) else self.typesystem.get_type(type_)
        if not self.typesystem.is_instance_of(t, TYPE_NAME_ANNOTATION):
            raise TypeError(
                f"Type [{t.name}] is not a subtype of [{TYPE_NAME_ANNOTATION}]; "
                f"{operation} only operates on annotation types"
            )
        return t

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
        seeds: Optional[Iterable[FeatureStructure]] = None,
    ) -> Iterable[FeatureStructure]:
        """This function traverses the whole CAS in order to find all directly and indirectly referenced
        feature structures. Traversing is needed as it can be that a feature structure is not added to the sofa but
        referenced by another feature structure as a feature."""
        all_fs = {}

        openlist: list[FeatureStructure] = []
        if seeds is not None:  # Using "is not None" to distinguish empty seeds from not using seeds at all
            openlist.extend(seeds)
        else:
            for sofa in self.sofas:
                view = self.get_view(sofa.sofaID)
                openlist.extend(view.select_all_fs())

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
                            if v.head and v.head.xmiID not in all_fs:
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

    def deep_copy(self, copy_typesystem: bool = False) -> "Cas":
        """
        Create and return a deep copy of this CAS object.
        All feature structures, views, and sofas are copied. If `copy_typesystem` is True, the typesystem is also deep-copied;
        otherwise, the original typesystem is shared between the original and the copy.
        Args:
            copy_typesystem (bool): Whether to copy the original typesystem or not. If True, the typesystem is deep-copied.
        Returns:
            Cas: A deep copy of this CAS object.
        """
        ts = self.typesystem
        if copy_typesystem:
            ts = self.typesystem.to_xml()
            ts = load_typesystem(ts)

        cas_copy = Cas(ts, lenient=self._lenient)

        cas_copy._views = {}
        cas_copy._sofas = {}

        def _collect_fs_list_references(fs_list: FeatureStructure) -> List[Optional[int]]:
            referenced_list = []
            current = fs_list

            while hasattr(current, FEATURE_BASE_NAME_HEAD):
                head = current.head
                if head is None:
                    referenced_list.append(None)
                elif hasattr(head, "xmiID") and head.xmiID is not None:
                    referenced_list.append(head.xmiID)
                else:
                    warnings.warn("FSList item without xmiID encountered during deep copy; preserving as None in copy.")
                    referenced_list.append(None)

                current = current.tail

            return referenced_list

        def _build_fs_list(referenced_list: List[Optional[int]]) -> FeatureStructure:
            current = ts.get_type("uima.cas.EmptyFSList")()

            for reference_id in reversed(referenced_list):
                node = ts.get_type("uima.cas.NonEmptyFSList")()
                node.tail = current
                node.head = all_copied_fs.get(reference_id) if reference_id is not None else None
                current = node

            return current

        for sofa in self.sofas:
            sofa_copy = Sofa(
                sofaID=sofa.sofaID,
                sofaNum=sofa.sofaNum,
                type=ts.get_type(sofa.type.name),
                xmiID=sofa.xmiID,
            )
            sofa_copy.mimeType = sofa.mimeType
            sofa_copy.sofaArray = sofa.sofaArray
            sofa_copy.sofaString = sofa.sofaString
            sofa_copy.sofaURI = sofa.sofaURI

            cas_copy._sofas[sofa_copy.sofaID] = sofa_copy
            cas_copy._views[sofa_copy.sofaID] = View(sofa=sofa_copy)

        # Set the current view to the `_InitialView` entry in the copied CAS.
        # (`Cas.__init__` creates an `_InitialView`; here we point the current
        # view at that entry in the `cas_copy._views` mapping so subsequent
        # `add()` calls index into the initial view by default.)
        cas_copy._current_view = cas_copy._views["_InitialView"]

        references = dict()
        referenced_arrays = dict()
        referenced_fs_arrays = dict()
        referenced_primitive_arrays = dict()
        referenced_lists = dict()
        # for primitive lists (e.g. IntegerList) we collect primitive head values
        referenced_primitive_lists = dict()

        all_copied_fs = dict()
        referenced_view = defaultdict(list)

        for view in self.views:
            for member in view.get_all_fs():
                if hasattr(member, "xmiID") and member.xmiID is not None:
                    if view.sofa.sofaID not in referenced_view[member.xmiID]:
                        referenced_view[member.xmiID].append(view.sofa.sofaID)

        # Ensure sofa.sofaArray feature structures are discovered even when they
        # are not indexed in any view. `_find_all_fs(seeds=...)` replaces the
        # default traversal roots, so we include both the original indexed view
        # members and any sofaArray roots here.
        traversal_seeds = []
        for sofa in self.sofas:
            traversal_seeds.extend(self.get_view(sofa.sofaID).select_all_fs())
            if getattr(sofa, "sofaArray", None) is not None:
                traversal_seeds.append(sofa.sofaArray)

        for fs in self._find_all_fs(seeds=traversal_seeds):
            try:
                t = ts.get_type(fs.type.name)
            except TypeNotFoundError as e:
                raise TypeNotFoundError(
                    f"deep_copy() cannot copy feature structure of type '{fs.type.name}': "
                    f"the type is not present in the target typesystem. This can happen when "
                    f"the source CAS was loaded leniently against an incomplete typesystem and "
                    f"contains feature structures whose types were not declared. deep_copy() "
                    f"requires every feature structure's type to be present in the typesystem."
                ) from e
            fs_copy = t()

            if t.name == TYPE_NAME_FS_ARRAY and fs.elements is not None:
                standalone_fs_array_member_ids = []
                for item in fs.elements:
                    if item is None:
                        standalone_fs_array_member_ids.append(None)
                    elif hasattr(item, "xmiID") and item.xmiID is not None:
                        standalone_fs_array_member_ids.append(item.xmiID)
                    else:
                        warnings.warn(
                            f"Standalone FSArray {fs.xmiID} contains an unidentifiable item; preserving as None in copy."
                        )
                        standalone_fs_array_member_ids.append(None)

                referenced_fs_arrays[fs.xmiID] = standalone_fs_array_member_ids
            elif t.supertype.name == TYPE_NAME_ARRAY_BASE and fs.elements is not None:
                referenced_primitive_arrays[fs.xmiID] = list(fs.elements)

            for feature in t.all_features:
                if t.supertype.name == TYPE_NAME_ARRAY_BASE and feature.name == "elements":
                    continue

                if ts.is_primitive(feature.rangeType):
                    fs_copy[feature.name] = fs.get(feature.name)
                elif ts.is_primitive_collection(feature.rangeType):
                    val = fs.get(feature.name)
                    if val is None:
                        continue

                    if feature.multipleReferencesAllowed and hasattr(val, "xmiID") and val.xmiID is not None:
                        references.setdefault(feature.name, [])
                        references[feature.name].append((fs.xmiID, val.xmiID))
                        continue

                    # Distinguish primitive arrays (have `elements`) from primitive lists (use head/tail).
                    # Lists may be declared with the abstract base type (e.g. IntegerList) or with a
                    # concrete subtype (e.g. NonEmptyIntegerList); the lookup handles both.
                    abstract_list_name = _PRIMITIVE_LIST_BASE_TYPE.get(feature.rangeType.name)
                    if ts.is_array(feature.rangeType):
                        fs_copy[feature.name] = ts.get_type(feature.rangeType.name)()
                        # shallow-copy the elements list to avoid sharing the same list object
                        fs_copy[feature.name].elements = list(val.elements)
                    elif abstract_list_name is not None:
                        # collect primitive values from head/tail style lists
                        current = val
                        prim_list = []
                        while hasattr(current, FEATURE_BASE_NAME_HEAD):
                            head = getattr(current, FEATURE_BASE_NAME_HEAD)
                            prim_list.append(head)
                            current = current.tail

                        # store the primitive list values along with the abstract list base name
                        # so the rebuild step can derive Empty*/NonEmpty* concrete type names.
                        referenced_primitive_lists.setdefault(fs.xmiID, {})
                        referenced_primitive_lists[fs.xmiID][feature.name] = (
                            abstract_list_name,
                            prim_list,
                        )
                    else:
                        warnings.warn(
                            f"Primitive collection feature '{feature.name}' on FS {fs.xmiID} has range type "
                            f"'{feature.rangeType.name}' which is neither a primitive array nor a primitive list; "
                            "value not copied."
                        )
                elif ts.is_array(feature.rangeType):
                    val = fs[feature.name]
                    if val is None:
                        continue

                    # If the array itself may be shared (multipleReferencesAllowed), preserve
                    # its identity by treating it like any other FS reference and wiring it
                    # up later via `references`. Only inline-copy arrays when they are not
                    # declared shareable.
                    if feature.multipleReferencesAllowed and hasattr(val, "xmiID") and val.xmiID is not None:
                        references.setdefault(feature.name, [])
                        references[feature.name].append((fs.xmiID, val.xmiID))
                    else:
                        fs_copy[feature.name] = ts.get_type(TYPE_NAME_FS_ARRAY)()
                        # collect referenced xmiIDs for mapping later and preserve None placeholders
                        array_feature_member_ids = []
                        for item in val.elements:
                            if item is None:
                                array_feature_member_ids.append(None)
                            elif hasattr(item, "xmiID") and item.xmiID is not None:
                                array_feature_member_ids.append(item.xmiID)
                            else:
                                warnings.warn(
                                    f"Array feature '{feature.name}' of FS {fs.xmiID} contains an unidentifiable item; preserving as None in copy."
                                )
                                array_feature_member_ids.append(None)
                        referenced_arrays.setdefault(fs.xmiID, {})
                        referenced_arrays[fs.xmiID][feature.name] = array_feature_member_ids
                elif ts.is_list(feature.rangeType):
                    val = fs[feature.name]
                    if val is None:
                        continue

                    if feature.multipleReferencesAllowed and hasattr(val, "xmiID") and val.xmiID is not None:
                        references.setdefault(feature.name, [])
                        references[feature.name].append((fs.xmiID, val.xmiID))
                    else:
                        referenced_lists.setdefault(fs.xmiID, {})
                        referenced_lists[fs.xmiID][feature.name] = _collect_fs_list_references(val)
                elif feature.rangeType.name == TYPE_NAME_SOFA:
                    # ignore sofa references
                    pass
                else:
                    val = fs[feature.name]
                    # If the original feature value is None, preserve it without warning
                    if val is None:
                        continue
                    if hasattr(val, "xmiID") and val.xmiID is not None:
                        references.setdefault(feature.name, [])
                        references[feature.name].append((fs.xmiID, val.xmiID))
                    else:
                        warnings.warn(
                            f'Original non-primitive feature "{feature.name}" was not copied from feature structure {fs.xmiID}.'
                        )

            fs_copy.xmiID = fs.xmiID
            all_copied_fs[fs_copy.xmiID] = fs_copy

        # set references to single objects
        for feature, pairs in references.items():
            for current_ID, reference_ID in pairs:
                try:
                    all_copied_fs[current_ID][feature] = all_copied_fs[reference_ID]
                except KeyError:
                    warnings.warn(
                        f"Reference {reference_ID} not found for feature '{feature}' of feature structure {current_ID}"
                    )

        # set references for objects in arrays
        for current_ID, arrays in referenced_arrays.items():
            for feature, array_member_ids in arrays.items():
                elements = []
                for reference_ID in array_member_ids:
                    if reference_ID is None:
                        elements.append(None)
                        continue
                    try:
                        elements.append(all_copied_fs[reference_ID])
                    except KeyError:
                        warnings.warn(
                            f"Reference {reference_ID} not found for array feature '{feature}' of feature structure {current_ID}; inserting None."
                        )
                        elements.append(None)
                all_copied_fs[current_ID][feature].elements = elements

        for current_ID, fs_array_member_ids in referenced_fs_arrays.items():
            elements = []
            for reference_ID in fs_array_member_ids:
                if reference_ID is None:
                    elements.append(None)
                    continue
                try:
                    elements.append(all_copied_fs[reference_ID])
                except KeyError:
                    warnings.warn(
                        f"Reference {reference_ID} not found for standalone FSArray {current_ID}; inserting None."
                    )
                    elements.append(None)
            all_copied_fs[current_ID].elements = elements

        for current_ID, elements in referenced_primitive_arrays.items():
            all_copied_fs[current_ID].elements = list(elements)

        # rebuild FSList features from copied members
        for current_ID, lists in referenced_lists.items():
            for feature, fs_list_member_ids in lists.items():
                all_copied_fs[current_ID][feature] = _build_fs_list(fs_list_member_ids)

        # rebuild primitive head/tail lists (e.g. IntegerList, FloatList, StringList)
        for current_ID, lists in referenced_primitive_lists.items():
            for feature, (list_type_name, primitive_values) in lists.items():
                # derive Empty/NonEmpty concrete type names from the abstract list type
                suffix = list_type_name.split(".")[-1]
                empty_name = f"uima.cas.Empty{suffix}"
                nonempty_name = f"uima.cas.NonEmpty{suffix}"

                current = ts.get_type(empty_name)()
                for value in reversed(primitive_values):
                    node = ts.get_type(nonempty_name)()
                    node.tail = current
                    node.head = value
                    current = node

                all_copied_fs[current_ID][feature] = current

        # ensure Sofa.sofaArray references point to the copied feature structures
        # Use the original CAS's sofas to locate the original sofaArray objects
        # (safer than relying on sofa_copy.sofaArray pointing back to the original
        # object in all cases) and remap them to the copied FS when available.
        for orig_sofa in self.sofas:
            sofa_copy = cas_copy._sofas.get(orig_sofa.sofaID)
            if sofa_copy is None:
                continue
            orig_sofa_array = getattr(orig_sofa, "sofaArray", None)
            if hasattr(orig_sofa_array, "xmiID") and orig_sofa_array.xmiID in all_copied_fs:
                sofa_copy.sofaArray = all_copied_fs[orig_sofa_array.xmiID]

        # Add only original view members back to the copied indices. Referenced
        # feature structures that were not indexed in any original view remain
        # reachable transitively and will still be serialized by `_find_all_fs()`.
        feature_structures = sorted(all_copied_fs.values(), key=lambda f: f.xmiID, reverse=False)
        for item in feature_structures:
            if not hasattr(item, "xmiID") or item.xmiID is None:
                continue

            view_names = referenced_view.get(item.xmiID)
            if not view_names:
                continue

            # Use the normal add-path once so FS with a `sofa` feature are rebound
            # to the copied sofa in their primary view. Any additional view
            # memberships are restored by indexing the same FS directly to avoid
            # mutating its `sofa` repeatedly.
            cas_copy._current_view = cas_copy._views[view_names[0]]
            cas_copy.add(item, keep_id=True)

            for view_name in view_names[1:]:
                cas_copy._views[view_name].add_annotation_to_index(item)

        cas_copy._xmi_id_generator = IdGenerator(initial_id=self._xmi_id_generator._next_id)
        cas_copy._sofa_num_generator = IdGenerator(initial_id=self._sofa_num_generator._next_id)

        # Restore the active view on the copy to match the source CAS' current view.
        # During re-indexing we may have set `cas_copy._current_view` multiple
        # times; ensure the returned copy has the same active sofa as `self`.
        try:
            active_sofa_id = self.get_sofa().sofaID
        except Exception:
            active_sofa_id = "_InitialView"

        if active_sofa_id in cas_copy._views:
            cas_copy._current_view = cas_copy._views[active_sofa_id]

        return cas_copy


def _sort_func(a: FeatureStructure) -> Tuple[int, int, int]:
    xmi_id = getattr(a, "xmiID", None)
    tiebreaker = xmi_id if xmi_id is not None else id(a)
    if is_annotation(a):
        return a.begin, a.end, tiebreaker
    # Non-annotation feature structures sort after annotations.
    return sys.maxsize, sys.maxsize, tiebreaker
