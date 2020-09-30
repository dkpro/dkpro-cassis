import difflib
from typing import IO, Union

import lxml_asserts
from lxml import etree


def assert_xml_equal(actual: Union[IO, str], expected: Union[IO, str]):
    """ Checks whether the XML trees behind `actual` and `expected` are equal.

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


def _to_etree(source: Union[IO, str]) -> etree.Element:
    parser = etree.XMLParser(remove_blank_text=True)

    if isinstance(source, str):
        return etree.fromstring(source.encode("utf-8"), parser=parser)
    else:
        return etree.parse(source, parser=parser).getroot()
