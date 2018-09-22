from typing import List

from collections import namedtuple

Sofa = namedtuple('Sofa', ['id', 'sofaNum', 'sofaID', 'sofaString', 'mimeType'])
View = namedtuple('View', ['sofa', 'members'])


class Cas():

    def __init__(self, namespaces, sofas, views):
        self.namespaces = namespaces
        self._sofas = {}
        self.views = views

        for sofa in sofas:
            self._sofas[sofa.id] = sofa

    def get_sofa(self, sofa_id: str) -> Sofa:
        return self._sofas[sofa_id]

    @property
    def sofas(self) -> List[Sofa]:
        return list(self._sofas.values())
