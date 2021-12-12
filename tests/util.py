import difflib
import json
from typing import IO, Union

import lxml_asserts
from lxml import etree


def assert_xml_equal(actual: Union[IO, str], expected: Union[IO, str]):
    """Checks whether the XML trees behind `actual` and `expected` are equal.

    Args:
        actual: The actual XML
        expected: The expected XML

    Throws:
        AssertionError when xml(actual) != xml(expected)
    """
    e1 = _to_etree(actual)
    e2 = _to_etree(expected)

    try:
        lxml_asserts.assert_xml_equal(e1, e2)
    except AssertionError as e:
        # For debugging purposes, the trees are saved to later inspect their contents
        s1 = etree.tostring(e1, pretty_print=True).decode("utf-8")
        s2 = etree.tostring(e2, pretty_print=True).decode("utf-8")

        with open("actual.xml", "w") as f:
            f.write(s1)

        with open("expected.xml", "w") as f:
            f.write(s2)

        with open("difference.diff", "w") as f:
            diff = difflib.unified_diff(s1.splitlines(), s2.splitlines(), fromfile="Actual", tofile="Expected")
            diff_string = "\n".join(diff)
            f.write(diff_string)

        raise e


def assert_json_equal(actual: str, expected: Union[IO, str], sort_keys: bool = False):
    """Checks whether the JSON trees behind `actual` and `expected` are equal.

    Args:
        actual: The actual JSON
        expected: The expected JSON

    Throws:
        AssertionError when json(actual) != json(expected)
    """
    if isinstance(actual, str):
        actual = json.loads(actual)

    if isinstance(expected, str):
        expected = json.loads(expected)

    actual_json = json.dumps(actual, sort_keys=sort_keys, indent=2)
    expected_json = json.dumps(expected, sort_keys=sort_keys, indent=2)

    try:
        assert actual_json == expected_json
    except AssertionError as e:
        # For debugging purposes, the trees are saved to later inspect their contents
        with open("actual.json", "w") as f:
            f.write(actual_json)

        with open("expected.json", "w") as f:
            f.write(expected_json)

        with open("difference.diff", "w") as f:
            diff = difflib.unified_diff(
                actual_json.splitlines(), expected_json.splitlines(), fromfile="Actual", tofile="Expected"
            )
            diff_string = "\n".join(diff)
            f.write(diff_string)

        raise e


def _to_etree(source: Union[IO, str]) -> etree.Element:
    parser = etree.XMLParser(remove_blank_text=True)

    if isinstance(source, str):
        return etree.fromstring(source.encode("utf-8"), parser=parser)
    else:
        return etree.parse(source, parser=parser).getroot()
