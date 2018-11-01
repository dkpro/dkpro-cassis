from collections import defaultdict
from io import BytesIO
from itertools import chain
from pathlib import Path
import sys
from typing import Dict, Iterator, List, Union, Tuple, Optional

import attr

from sortedcontainers import SortedKeyList

from cassis.typesystem import AnnotationBase


@attr.s(slots=True)
class Sofa:
    """Each CAS has one or more Subject of Analysis (SofA)"""

    sofaNum = attr.ib()  # type: int # The sofaNum
    xmiID = attr.ib(default=None)  # type: int # The XMI id
    sofaID = attr.ib(default=None)  # type: str # The sofa ID
    sofaString = attr.ib(default=None)  # type: str # The text corresponding to this sofa
    mimeType = attr.ib(default=None)  # type: str # The mime type of the `sofaString`


@attr.s(slots=True)
class View:
    """A view into a CAS contains a subset of annotations"""

    sofa = attr.ib()  # type: int # The sofa belonging to this view
    members = attr.ib()  # type: List[int] # xmi IDs of the annotations beloning to this view


class Cas:
    """A CAS object is a container for text (sofa) and annotations"""

    def __init__(
        self,
        annotations: List[AnnotationBase] = None,
        namespaces: Dict[str, str] = None,
        sofas: List[Sofa] = None,
        views: List[View] = None,
    ):
        self.namespaces = namespaces or {}
        self._sofas = {}
        self.views = views or []
        # Annotations are sorted by begin index first (smaller first). If begin
        #  is equal, sort by end index, smaller first. This is the same as
        # comparing a Python tuple of (begin, end)
        self._annotations = defaultdict(lambda: SortedKeyList(key=_sort_func))
        _annotations = annotations or []
        for annotation in _annotations:
            self._annotations[annotation.type].add(annotation)

        # Find maximum id. This has to be done before creating the default sofa
        maximum_xmi_id = 1
        for obj in chain(sofas or [], _annotations):
            if obj.xmiID and obj.xmiID > maximum_xmi_id:
                maximum_xmi_id = obj.xmiID

        self.maximum_xmiID = maximum_xmi_id

        # Handle sofas
        if sofas is None or len(sofas) == 0:
            _sofas = [Sofa(sofaNum=1, xmiID=self._get_next_id())]
        else:
            _sofas = sofas

        for sofa in _sofas:
            self._sofas[sofa.xmiID] = sofa

    def add_annotation(self, annotation: AnnotationBase):
        """Adds an annotation to this Cas

        Args:
            annotation: The annotation to add

        """
        if annotation.xmiID is None:
            annotation.xmiID = self._get_next_id()

        self._annotations[annotation.type].add(annotation)

    def get_covered_text(self, annotation: AnnotationBase) -> str:
        """Gets the text that is covered by `annotation`

        Args:
            annotation: The annotation whose covered text is to be retreived

        Returns:
            The text covered by `annotation`

        """
        sofa = self.get_sofa(annotation.sofa)
        return sofa.sofaString[annotation.begin : annotation.end]

    def select(self, typename: str) -> Iterator[AnnotationBase]:
        """Finds all annotations of type `typename`

        Args:
            typename: The name of the type whose annotation instances are to be found

        Returns:
            An iterator over all annotations of type `typename`

        """
        for annotation in self._annotations[typename]:
            yield annotation

    def select_covered(self, typename: str, covering_annotation: AnnotationBase) -> Iterator[AnnotationBase]:
        """Returns an iterator over covered annotations

        Return all annotations that are covered

        Only returns annotations that are fully covered, overlapping annotations
        are ignored.

        Args:
            typename: The type name of the annotations to be returned
            covering_annotation: The name of the annotation which covers

        Returns:
            an iterator over covered annotations

        """
        c_begin = covering_annotation.begin
        c_end = covering_annotation.end

        annotations = self._annotations[typename]

        # The entry point is the index of the first annotation whose `begin`
        # is equal or higher than the `begin` of the covering annotation
        entry_point = annotations.bisect_key_left((c_begin, c_begin))

        for annotation in annotations[entry_point:]:
            if annotation.begin >= c_begin and annotation.end <= c_end:
                yield annotation

            if annotation.begin > c_end:
                break

    def select_all(self) -> Iterator[AnnotationBase]:
        """Finds all annotations in this Cas

        Returns:
            An iterator over all annotations in this Cas

        """
        for annotations in self._annotations.values():
            for annotation in annotations:
                yield annotation

    def get_sofa(self, sofa_id: int) -> Sofa:
        """ Finds the sofa with the given id.

        Args:
            sofa_id: The id of the sofa to find.

        Returns:
            The sofa with id `sofa_id`

        """
        return self._sofas[sofa_id]

    @property
    def sofas(self) -> List[Sofa]:
        """Finds all sofas that this CAS manages

        Returns:
            The list of all sofas belonging to this CAS

        """
        return list(self._sofas.values())

    def _get_next_id(self):
        self.maximum_xmiID += 1
        return self.maximum_xmiID

    def to_xmi(self, path: Union[str, Path, None] = None) -> Optional[str]:
        """Creates a XMI representation of this CAS.

        Args:
            path: File path, if `None` is provided the result is returned as a string.

        Returns:
            If `path` is None, then the XMI representation of this CAS is returned as a string

        """
        from cassis.xmi import CasXmiSerializer

        serializer = CasXmiSerializer()

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


def _sort_func(a: AnnotationBase) -> Tuple[int, int]:
    d = a.__slots__
    if "begin" in d and "end" in d:
        return (a.begin, a.end)
    else:
        return (sys.maxsize, sys.maxsize)
