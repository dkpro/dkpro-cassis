import json

from tests.fixtures import *
from tests.test_files.test_cas_generators import MultiTypeRandomCasGenerator
from tests.util import assert_json_equal

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_files")

FIXTURES = [
    (os.path.join(FIXTURE_DIR, "json", "fs_as_array", "ser-ref", "casWithSofaDataArray")),
    (os.path.join(FIXTURE_DIR, "json", "fs_as_array", "ser-ref", "casWithSofaDataURI")),
    (os.path.join(FIXTURE_DIR, "json", "fs_as_array", "ser-ref", "casWithText")),
    (os.path.join(FIXTURE_DIR, "json", "fs_as_array", "ser-ref", "casWithTextAndAnnotation")),
]


@pytest.mark.parametrize("json_path", FIXTURES)
def test_deserialization_serialization(json_path):
    with open(os.path.join(json_path, "data.json"), "rb") as f:
        cas = load_cas_from_json(f)

    with open(os.path.join(json_path, "data.json"), "rb") as f:
        expected_json = json.load(f)

    actual_json = cas.to_json()

    assert_json_equal(actual_json, expected_json)


def test_serialization_deserialization():
    generator = MultiTypeRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        generator.type_count = i + 1
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        expected_json = randomized_cas.to_json(pretty_print=True)

        loaded_cas = load_cas_from_json(expected_json)
        actual_json = loaded_cas.to_json()

        assert_json_equal(actual_json, expected_json)
