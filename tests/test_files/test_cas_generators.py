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


class MultiFeatureRandomCasGenerator:
    STRING_VALUES = ["abc", "abcdef", None, "", "ghijklm", "a", "b"]
    BYTE_VALUES = [1, 0, -1, 127, -128, 9, -9]
    LONG_VALUES = [1, 0, -1, 9223372036854775807, -9223372036854775808, 11, -11]
    SHORT_VALUES = [1, 0, -1, 32767, -32768, 22, -22]
    DOUBLE_VALUES = [1, 0, -1, 999999999999, -999999999999, 33, -33.33]
    FLOAT_VALUES = [1, 0, -1, 999999999999, -999999999999, 17, -22.33]
    BOOL_VALUES = [True, False]

    def __init__(self):
        self.size = 10
        self.rnd = Random()

    def generate_type_system(self) -> TypeSystem:
        typesystem = TypeSystem()
        Akof = typesystem.create_type("akof", TYPE_NAME_TOP, "all kinds of features")
        typesystem.add_feature(Akof, "akofInt", TYPE_NAME_INTEGER)
        typesystem.add_feature(Akof, "akofFs", TYPE_NAME_TOP)
        typesystem.add_feature(Akof, "akofFloat", TYPE_NAME_FLOAT)
        typesystem.add_feature(Akof, "akofDouble", TYPE_NAME_DOUBLE)
        typesystem.add_feature(Akof, "akofLong", TYPE_NAME_LONG)
        typesystem.add_feature(Akof, "akofShort", TYPE_NAME_SHORT)
        typesystem.add_feature(Akof, "akofByte", TYPE_NAME_BYTE)
        typesystem.add_feature(Akof, "akofBoolean", TYPE_NAME_BOOLEAN)
        typesystem.add_feature(Akof, "akofString", TYPE_NAME_STRING)
        # typesystem.add_feature(Akof, "akofAInt", TYPE_NAME_INTEGER_ARRAY)
        # typesystem.add_feature(Akof, "akofAFs", TYPE_NAME_FS_ARRAY)
        # typesystem.add_feature(Akof, "akofAFloat", TYPE_NAME_FLOAT_ARRAY)
        # typesystem.add_feature(Akof, "akofADouble", TYPE_NAME_DOUBLE_ARRAY)
        # typesystem.add_feature(Akof, "akofALong", TYPE_NAME_LONG_ARRAY)
        # typesystem.add_feature(Akof, "akofAShort", TYPE_NAME_SHORT_ARRAY)
        # typesystem.add_feature(Akof, "akofAByte", TYPE_NAME_BYTE_ARRAY)
        # typesystem.add_feature(Akof, "akofABoolean", TYPE_NAME_BOOLEAN_ARRAY)
        # typesystem.add_feature(Akof, "akofAString", TYPE_NAME_STRING_ARRAY)
        return typesystem

    def generate_cas(self, typesystem: TypeSystem) -> Cas:
        feature_structures = []

        cas = Cas(typesystem)

        for i in range(0, self.size):
            feature_structures.append(self._makeAkof(cas))

        # Randomly link feature structures to each other
#        FSArray = cas.typesystem.get_type(TYPE_NAME_FS_ARRAY)
        for fs in feature_structures:
            fs.akofFs = self.rnd.choice(feature_structures)
#            fs.akofAFs = FSArray(
#                elements=[self.rnd.choice(feature_structures) for i in range(0, self.rnd.randint(1, 3))]
#            )

        cas.add_annotations(feature_structures)

        return cas

    def _makeAkof(self, cas: Cas) -> Any:
        Akof = cas.typesystem.get_type("akof")
        # IntegerArray = cas.typesystem.get_type(TYPE_NAME_INTEGER_ARRAY)
        # FloatArray = cas.typesystem.get_type(TYPE_NAME_FLOAT_ARRAY)
        # DoubleArray = cas.typesystem.get_type(TYPE_NAME_DOUBLE_ARRAY)
        # LongArray = cas.typesystem.get_type(TYPE_NAME_LONG_ARRAY)
        # ShortArray = cas.typesystem.get_type(TYPE_NAME_SHORT_ARRAY)
        # ByteArray = cas.typesystem.get_type(TYPE_NAME_BYTE_ARRAY)
        # BooleanArray = cas.typesystem.get_type(TYPE_NAME_BOOLEAN_ARRAY)
        # StringArray = cas.typesystem.get_type(TYPE_NAME_STRING_ARRAY)
        akof = Akof()
        akof.akofInt = self.rnd.randint(-2147483648, 2147483647)
        akof.akofFloat = self.rnd.choice(self.FLOAT_VALUES)
        akof.akofDouble = self.rnd.choice(self.DOUBLE_VALUES)
        akof.akofLong = self.rnd.choice(self.LONG_VALUES)
        akof.akofShort = self.rnd.choice(self.SHORT_VALUES)
        akof.akofByte = self.rnd.choice(self.BYTE_VALUES)
        akof.akofBoolean = self.rnd.choice(self.BOOL_VALUES)
        akof.akofString = self.rnd.choice(self.STRING_VALUES)
        # akof.akofAInt = IntegerArray(
        #     elements=[self.rnd.randint(-2147483648, 2147483647) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofAFloat = FloatArray(
        #     elements=[self.rnd.choice(self.FLOAT_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofADouble = DoubleArray(
        #     elements=[self.rnd.choice(self.DOUBLE_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofALong = LongArray(
        #     elements=[self.rnd.choice(self.LONG_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofAShort = ShortArray(
        #     elements=[self.rnd.choice(self.SHORT_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofAByte = ByteArray(
        #     elements=[self.rnd.choice(self.BYTE_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofABoolean = BooleanArray(
        #     elements=[self.rnd.choice(self.BOOL_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        # akof.akofAString = StringArray(
        #     elements=[self.rnd.choice(self.STRING_VALUES) for i in range(0, self.rnd.randint(1, 3))]
        # )
        return akof
