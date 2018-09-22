from collections import namedtuple
import re
from typing import List

import attr


def _string_to_valid_classname(name: str):
    return re.sub('[^a-zA-Z_]', '_', name).upper()


@attr.s
class Feature():
    name = attr.ib()
    description = attr.ib()
    rangeTypeName = attr.ib()


@attr.s
class Type():
    name = attr.ib()
    description = attr.ib()
    supertypeName = attr.ib()
    features = attr.ib()
    constructor = attr.ib(init=False, cmp=False)

    def __attrs_post_init__(self):
        name = _string_to_valid_classname(self.name)
        common_fields = ['type', 'xmiID', 'sofa', 'begin', 'end']
        fields = common_fields + [feature.name for feature in self.features]
        constructor = namedtuple(name, fields)

        # Set the default values for all fields to None
        constructor.__new__.__defaults__ = (None,) * len(constructor._fields)
        self.constructor = constructor

    def __call__(self, xmiID=None, sofa=None, begin=None, end=None, **kwargs):
        return self.constructor(type=self.name, xmiID=xmiID, sofa=sofa, begin=begin, end=end, **kwargs)


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
            return FallbackType

    def __len__(self) -> int:
        return len(self._types)