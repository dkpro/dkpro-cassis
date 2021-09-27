from random import Random
from timeit import default_timer as timer

import pytest

from cassis import load_cas_from_json, load_cas_from_xmi
from tests.test_files.test_cas_generators import MultiFeatureRandomCasGenerator

generator = MultiFeatureRandomCasGenerator()
generator.rnd = Random(123456)
generator.size = 1000
iterations = 100

typesystem = generator.generate_type_system()
randomized_cas = generator.generate_cas(typesystem)

randomized_cas_xmi = randomized_cas.to_xmi()
randomized_cas_xmi_bytes = randomized_cas_xmi.encode("utf-8")

randomized_cas_json = randomized_cas.to_json()
randomized_cas_json_bytes = randomized_cas_json.encode("utf-8")


@pytest.mark.performance
def test_xmi_serialization_performance():
    start = timer()
    for i in range(0, iterations):
        randomized_cas.to_xmi()
    end = timer()

    print(
        f"XMI: Serializing {iterations} CASes with {generator.size} each took {end - start} seconds ({len(randomized_cas_xmi_bytes)} bytes each)"
    )


@pytest.mark.performance
def test_json_serialization_performance():
    start = timer()
    for i in range(0, iterations):
        randomized_cas.to_json()
    end = timer()

    print(
        f"JSON: Serializing {iterations} CASes with {generator.size} each took {end - start} seconds ({len(randomized_cas_json_bytes)} bytes each)"
    )


@pytest.mark.performance
def test_xmi_deserialization_performance():
    start = timer()
    for i in range(0, iterations):
        load_cas_from_xmi(randomized_cas_xmi, typesystem)
    end = timer()

    print(
        f"XMI: Deserializing {iterations} CASes with {generator.size} each took {end - start} seconds ({len(randomized_cas_xmi_bytes)} bytes each)"
    )


@pytest.mark.performance
def test_json_deserialization_performance():
    start = timer()
    for i in range(0, iterations):
        load_cas_from_json(randomized_cas_json, typesystem)
    end = timer()

    print(
        f"JSON: Deserializing {iterations} CASes with {generator.size} each took {end - start} seconds ({len(randomized_cas_json_bytes)} bytes each)"
    )
