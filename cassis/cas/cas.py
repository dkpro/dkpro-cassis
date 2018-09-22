from typing import Any, Iterator, List

from collections import namedtuple

Sofa = namedtuple('Sofa', ['id', 'sofaNum', 'sofaID', 'sofaString', 'mimeType'])
View = namedtuple('View', ['sofa', 'members'])


class Cas():

    def __init__(self, namespaces, sofas, views, annotations: List[Any]):
        self.namespaces = namespaces
        self._sofas = {}
        self.views = views
        self._annotations = annotations

        for sofa in sofas:
            self._sofas[sofa.id] = sofa

    def get_sofa(self, sofa_id: str) -> Sofa:
        return self._sofas[sofa_id]

    @property
    def sofas(self) -> List[Sofa]:
        return list(self._sofas.values())

    def select(self, typename: str) -> Iterator[Any]:
        for annotation in self._annotations:
            if annotation.type == typename:
                yield annotation
