import pytest

from cassis.util import (
    covered_by,
    covering,
    colocated,
    overlapping,
    overlapping_at_begin,
    overlapping_at_end,
    following,
    preceding,
    beginning_with,
    ending_with,
)


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (5, 10, 0, 20, True),  # X inside Y
        (0, 10, 0, 10, True),  # equal
        (0, 5, 2, 10, False),  # starts before Y
        (5, 15, 0, 10, False),  # ends after Y
        (5, 5, 0, 10, True),  # zero-width inside
    ],
)
def test_covered_by(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert covered_by(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (0, 20, 5, 10, True),
        (0, 10, 0, 10, True),
        (2, 8, 0, 10, False),
        (0, 5, 5, 10, False),
        (5, 15, 0, 10, False),
    ],
)
def test_covering(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert covering(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (0, 10, 0, 10, True),
        (5, 5, 5, 5, True),
        (0, 5, 1, 5, False),
    ],
)
def test_colocated(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert colocated(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (5, 15, 10, 20, True),  # partial overlap
        (0, 5, 5, 10, False),  # touching at boundary is not overlap
        (5, 5, 0, 10, True),  # zero-width inside
        (5, 5, 5, 5, True),  # both zero-width same point
        (0, 10, 2, 8, True),  # containment
    ],
)
def test_overlapping(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert overlapping(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (0, 7, 5, 10, True),
        (0, 12, 5, 10, False),
        (5, 10, 0, 10, False),
    ],
)
def test_overlapping_at_begin(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert overlapping_at_begin(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (7, 12, 5, 10, True),
        (5, 10, 0, 10, False),
        (0, 12, 5, 10, False),
    ],
)
def test_overlapping_at_end(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert overlapping_at_end(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (10, 15, 0, 10, True),
        (11, 12, 0, 10, True),
    ],
)
def test_following(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert following(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (0, 5, 5, 10, True),
        (0, 4, 5, 10, True),
        (5, 6, 0, 5, False),
    ],
)
def test_preceding(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert preceding(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (0, 5, 0, 10, True),
        (1, 5, 0, 10, False),
    ],
)
def test_beginning_with(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert beginning_with(xb, xe, yb, ye) is expected


@pytest.mark.parametrize(
    "xb,xe,yb,ye,expected",
    [
        (0, 10, 5, 10, True),
        (0, 9, 5, 10, False),
    ],
)
def test_ending_with(xb: int, xe: int, yb: int, ye: int, expected: bool):
    assert ending_with(xb, xe, yb, ye) is expected
