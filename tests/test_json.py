import json

from tests.fixtures import *
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
