from collections import defaultdict, namedtuple
from typing import Any, Iterator, List

from sortedcontainers import SortedKeyList

from cassis.typesystem.typesystem import Annotation

Sofa = namedtuple('Sofa', ['id', 'sofaNum', 'sofaID', 'sofaString', 'mimeType'])
View = namedtuple('View', ['sofa', 'members'])


class Cas():

    def __init__(self, namespaces, sofas, views, annotations: List[Annotation]):
        self.namespaces = namespaces
        self._sofas = {}
        self.views = views
        # Annotations are sorted by begin index first (smaller first). If begin
        #  is equal, sort by end index, smaller first. This is the same as
        # comparing a Python tuple of (begin, end)
        self._annotations = defaultdict(lambda: SortedKeyList(key=lambda a: (a.begin, a.end)))
        for annotation in annotations:
            self._annotations[annotation.type].add(annotation)

        for sofa in sofas:
            self._sofas[sofa.id] = sofa

    def get_sofa(self, sofa_id: str) -> Sofa:
        return self._sofas[sofa_id]

    @property
    def sofas(self) -> List[Sofa]:
        return list(self._sofas.values())

    def select(self, typename: str) -> Iterator[Any]:
        for annotation in self._annotations[typename]:
            yield annotation

    def select_covered(self, typename, covered_typename):
        pass
