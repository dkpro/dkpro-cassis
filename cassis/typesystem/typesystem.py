import re
from typing import Callable, Dict, List, Iterator

import attr


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

    def __len__(self) -> int:
        return len(self._types)