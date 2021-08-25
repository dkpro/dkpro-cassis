from random import Random
from timeit import default_timer as timer

from cassis import load_cas_from_json, load_cas_from_xmi
from tests.test_files.test_cas_generators import MultiFeatureRandomCasGenerator

generator = MultiFeatureRandomCasGenerator()
generator.rnd = Random(123456)
generator.size = 1000
iterations = 100

typesystem = generator.generate_type_system()
randomized_cas = generator.generate_cas(typesystem)
randomized_cas_xmi = randomized_cas.to_xmi()
randomized_cas_json = randomized_cas.to_json()


def test_xmi_serialization_performance():
    start = timer()
    for i in range(0, iterations):
        if i % 10 == 0:
            print(".", end='')
        if i % 100 == 0:
            print(f"{i}")
        randomized_cas.to_xmi()
    end = timer()

    print(f"XMI: Serializing {iterations} CASes took {end - start} seconds")


def test_json_serialization_performance():
    start = timer()
    for i in range(0, iterations):
        if i % 10 == 0:
            print(".", end='')
        if i % 100 == 0:
            print(f"{i}")
        randomized_cas.to_json()
    end = timer()

    print(f"JSON: Serializing {iterations} CASes took {end - start} seconds")


def test_xmi_deserialization_performance():
    start = timer()
    for i in range(0, iterations):
        if i % 10 == 0:
            print(".", end='')
        if i % 100 == 0:
            print(f"{i}")
        load_cas_from_xmi(randomized_cas_xmi, typesystem)
    end = timer()

    print(f"XMI: Deserializing {iterations} CASes took {end - start} seconds")


def test_json_deserialization_performance():
    start = timer()
    for i in range(0, iterations):
        if i % 10 == 0:
            print(".", end='')
        if i % 100 == 0:
            print(f"{i}")
        load_cas_from_json(randomized_cas_json, typesystem)
    end = timer()

    print(f"JSON: Deserializing {iterations} CASes took {end - start} seconds")
