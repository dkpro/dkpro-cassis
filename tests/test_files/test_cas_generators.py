from random import Random

from cassis import Cas, TypeSystem
from cassis.typesystem import *


class MultiTypeRandomCasGenerator:
    def __init__(self):
        self.type_count = 10
        self.size = 10
        self.minimum_width = 0
        self.rnd = Random()

    def generate_type_system(self) -> TypeSystem:
        typesystem = TypeSystem()
        types = []

        for ti in range(0, self.type_count):
            type_name = f"test.Type{ti + 1}"
            if self.rnd.randint(0, 1) == 0 or not types:
                typesystem.create_type(type_name, TYPE_NAME_ANNOTATION)
            else:
                typesystem.create_type(type_name, self.rnd.choice(types))
            types.append(type_name)

        return typesystem

    def generate_cas(self, typesystem: TypeSystem) -> Cas:
        cas = Cas(typesystem)

        types = [t for t in typesystem.get_types()]
        types.remove(cas.typesystem.get_type(TYPE_NAME_DOCUMENT_ANNOTATION))
        self.rnd.shuffle(types)

        for n in range(0, self.size):
            for T in types:
                begin = self.rnd.randint(0, 100)
                end = self.rnd.randint(0, 30) + self.minimum_width
                fs = T(begin=begin, end=end)
                cas.add_annotation(fs)

        return cas
