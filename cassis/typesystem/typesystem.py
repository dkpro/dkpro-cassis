from collections import namedtuple

Type = namedtuple('TypeDescription', ['name', 'description', 'supertypeName', 'features'])
Feature = namedtuple('Feature', ['name', 'description', 'rangeTypeName'])

class TypeSystem():

    def __init__(self, types):
        self._types = {}
        for type in types:
            self._types[type.name] = type

    def has_type(self, typename):
        """

        Args:
            typename (str):

        Returns:

        """
        return typename in self._types

    def get_type(self, typename):
        """

        Args:
            typename (str):

        Returns:

        """
        return self._types[typename]

    def __len__(self):
        return len(self._types)