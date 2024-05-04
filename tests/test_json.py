import json

from cassis.typesystem import TYPE_NAME_ANNOTATION, TYPE_NAME_DOCUMENT_ANNOTATION, TypeSystemMode
from tests.fixtures import *
from tests.test_files.test_cas_generators import MultiFeatureRandomCasGenerator, MultiTypeRandomCasGenerator
from tests.util import assert_json_equal

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_files", "json")
SER_REF_DIR = os.path.join(FIXTURE_DIR, "fs_as_array", "ser-ref")
ONE_WAY_DIR = os.path.join(FIXTURE_DIR, "fs_as_array", "one-way")

ROUND_TRIP_FIXTURES = [
    (os.path.join(SER_REF_DIR, "casWithSofaDataArray"), []),
    (os.path.join(SER_REF_DIR, "casWithSofaDataURI"), []),
    (os.path.join(SER_REF_DIR, "casWithFloatingPointSpecialValues"), []),
    (os.path.join(SER_REF_DIR, "casWithText"), [[TYPE_NAME_DOCUMENT_ANNOTATION, 0, 15, "This is a test."]]),
    (
        os.path.join(SER_REF_DIR, "casWithoutTextButWithAnnotations"),
        [
            [TYPE_NAME_ANNOTATION, 0, 4, None],
            [TYPE_NAME_ANNOTATION, 5, 7, None],
            [TYPE_NAME_ANNOTATION, 8, 9, None],
            [TYPE_NAME_ANNOTATION, 10, 14, None],
        ],
    ),
    (
        os.path.join(SER_REF_DIR, "casWithTextAndAnnotations"),
        [
            [TYPE_NAME_ANNOTATION, 0, 4, "This"],
            [TYPE_NAME_ANNOTATION, 5, 7, "is"],
            [TYPE_NAME_ANNOTATION, 8, 9, "a"],
            [TYPE_NAME_ANNOTATION, 10, 14, "test"],
            [TYPE_NAME_DOCUMENT_ANNOTATION, 0, 14, "This is a test"],
        ],
    ),
    (
        os.path.join(SER_REF_DIR, "casWithEmojiUnicodeTextAndAnnotations"),
        [
            [TYPE_NAME_ANNOTATION, 0, 1, "🥳", b"\xf0\x9f\xa5\xb3"],
            [TYPE_NAME_ANNOTATION, 2, 6, "This"],
            [
                TYPE_NAME_ANNOTATION,
                7,
                12,
                "👳🏻\u200d♀️",
                b"\xf0\x9f\x91\xb3\xf0\x9f\x8f\xbb\xe2\x80\x8d\xe2\x99\x80\xef\xb8\x8f",
            ],
            [TYPE_NAME_ANNOTATION, 13, 15, "is"],
            [TYPE_NAME_ANNOTATION, 16, 17, "✆", b"\xe2\x9c\x86"],
            [TYPE_NAME_ANNOTATION, 18, 19, "a"],
            [
                TYPE_NAME_ANNOTATION,
                20,
                25,
                "🧔🏾\u200d♂️",
                b"\xf0\x9f\xa7\x94\xf0\x9f\x8f\xbe\xe2\x80\x8d\xe2\x99\x82\xef\xb8\x8f",
            ],
            [TYPE_NAME_ANNOTATION, 26, 30, "test"],
            [TYPE_NAME_ANNOTATION, 31, 32, "👻", b"\xf0\x9f\x91\xbb"],
            [TYPE_NAME_DOCUMENT_ANNOTATION, 0, 32, "🥳 This 👳🏻\u200d♀️ is ✆ a 🧔🏾\u200d♂️ test 👻"],
        ],
    ),
    (
        os.path.join(SER_REF_DIR, "casWithLeftToRightTextAndAnnotations"),
        [
            [TYPE_NAME_ANNOTATION, 0, 3, "هذا"],
            [TYPE_NAME_ANNOTATION, 4, 10, "اختبار"],
            [TYPE_NAME_DOCUMENT_ANNOTATION, 0, 10, "هذا اختبار"],
        ],
    ),
    (
        os.path.join(SER_REF_DIR, "casWithTraditionalChineseTextAndAnnotations"),
        [
            [TYPE_NAME_ANNOTATION, 0, 1, "這"],
            [TYPE_NAME_ANNOTATION, 1, 2, "是"],
            [TYPE_NAME_ANNOTATION, 2, 4, "一個"],
            [TYPE_NAME_ANNOTATION, 4, 6, "測試"],
            [TYPE_NAME_DOCUMENT_ANNOTATION, 0, 6, "這是一個測試"],
        ],
    ),
    (
        os.path.join(SER_REF_DIR, "casExtendingDocumentAnnotation"),
        [["de.tudarmstadt.ukp.dkpro.core.api.metadata.type.DocumentMetaData", 0, 16, "This is a test ."]],
    ),
]

ONE_WAY_FIXTURES = [
    (
        os.path.join(ONE_WAY_DIR, "casWithBadSofaFsOrder"),
        [["de.tudarmstadt.ukp.dkpro.core.api.metadata.type.DocumentMetaData", 0, 16, "This is a test ."]],
    ),
    (
        os.path.join(ONE_WAY_DIR, "tsv3-testSimpleSlotFeature"),
        [],
    ),
]


@pytest.mark.parametrize("json_path, annotations", ROUND_TRIP_FIXTURES)
def test_deserialization_serialization(json_path, annotations):
    with open(os.path.join(json_path, "data.json"), "rb") as f:
        cas = load_cas_from_json(f)

    with open(os.path.join(json_path, "data.json"), "rb") as f:
        expected_json = json.load(f)

    actual_json = cas.to_json(pretty_print=True)

    assert_json_equal(actual_json, expected_json, sort_keys=True)


@pytest.mark.parametrize("json_path, annotations", ONE_WAY_FIXTURES)
def test_deserialization_serialization_one_way(json_path, annotations):
    with open(os.path.join(json_path, "data.json"), "rb") as f:
        cas = load_cas_from_json(f)

    with open(os.path.join(json_path, "data-ref.json"), "rb") as f:
        expected_json = json.load(f)

    actual_json = cas.to_json(pretty_print=True)

    assert_json_equal(actual_json, expected_json, sort_keys=True)


def test_multi_type_random_serialization_deserialization():
    generator = MultiTypeRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        generator.type_count = i + 1
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_annotations()) for view in randomized_cas.views)}")
        expected_json = randomized_cas.to_json()

        loaded_cas = load_cas_from_json(expected_json)
        actual_json = loaded_cas.to_json()

        assert_json_equal(actual_json, expected_json)


def test_multi_feature_random_serialization_deserialization():
    generator = MultiFeatureRandomCasGenerator()
    for i in range(0, 10):
        generator.size = (i + 1) * 10
        typesystem = generator.generate_type_system()
        randomized_cas = generator.generate_cas(typesystem)
        print(f"CAS size: {sum(len(view.get_all_annotations()) for view in randomized_cas.views)}")
        expected_json = randomized_cas.to_json()

        loaded_cas = load_cas_from_json(expected_json)
        actual_json = loaded_cas.to_json()

        assert_json_equal(actual_json, expected_json)


@pytest.mark.parametrize("json_path, annotations", ROUND_TRIP_FIXTURES)
def test_unicode(json_path, annotations):
    with open(os.path.join(json_path, "data.json"), "rb") as f:
        cas = load_cas_from_json(f)

    actual_annotations = [
        [a.type.name, a.begin, a.end, a.get_covered_text()]
        for a in sorted(cas.select(TYPE_NAME_ANNOTATION), key=lambda k: k.type.name)
    ]
    expected_annotations = [a[0:4] for a in annotations]
    assert actual_annotations == expected_annotations

    for i in range(0, len(annotations)):
        expected = annotations[i]
        actual = actual_annotations[i]

        expected_covered_text = expected[3]
        actual_covered_text = actual[3]

        if not expected_covered_text:
            continue

        for n in range(len(actual_covered_text)):
            print(f"{n}: [{actual_covered_text[n]}] {hex(ord(actual_covered_text[n]))}")

        if len(expected) >= 5:
            expected_utf8_bytes = expected[4]
            actual_utf8_bytes = bytes(actual_covered_text, "UTF-8")
            assert actual_utf8_bytes == expected_utf8_bytes


def test_recursive_type_system():
    typesystem = TypeSystem()
    type_a = typesystem.create_type(name="example.TypeA")
    type_b = typesystem.create_type(name="example.TypeB")
    typesystem.create_feature(domainType=type_a, name="typeB", rangeType=type_b)
    typesystem.create_feature(domainType=type_b, name="typeA", rangeType=type_a)

    source_cas = Cas(typesystem=typesystem)
    target_cas = load_cas_from_json(source_cas.to_json(type_system_mode=TypeSystemMode.FULL))

    target_type_a = target_cas.typesystem.get_type("example.TypeA")
    target_type_b = target_cas.typesystem.get_type("example.TypeB")

    # We have to compare types by name below due to https://github.com/dkpro/dkpro-cassis/issues/270
    assert target_type_a is not None
    assert target_type_a.get_feature("typeB").rangeType.name == target_type_b.name
    assert target_type_b is not None
    assert target_type_b.get_feature("typeA").rangeType.name == target_type_a.name


def test_deserializing_type_system_if_child_type_is_defined_before_supertype():
    with open(os.path.join(FIXTURE_DIR, "child_type_before_parent.json"), "rb") as f:
        load_cas_from_json(f)
