import pytest

from delivery.range import InvalidRange, parse_single_range


def test_full_resource_without_range():
    assert parse_single_range(None, 100) == (0, 99, False)


def test_explicit_range_is_clamped():
    assert parse_single_range("bytes=10-", 100) == (10, 99, True)
    assert parse_single_range("bytes=10-120", 100) == (10, 99, True)


def test_suffix_range():
    assert parse_single_range("bytes=-10", 100) == (90, 99, True)
    assert parse_single_range("bytes=-1000", 100) == (0, 99, True)


@pytest.mark.parametrize("value", [
    "bytes=",
    "bytes=abc-def",
    "bytes=100-100",
    "bytes=10-9",
    "bytes=-0",
    "bytes=1-2,4-5",
    "items=1-2",
])
def test_invalid_ranges(value):
    with pytest.raises(InvalidRange):
        parse_single_range(value, 100)


def test_empty_resource_has_no_valid_range():
    with pytest.raises(InvalidRange):
        parse_single_range(None, 0)
