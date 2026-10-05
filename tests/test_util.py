"""Tests for the string helpers in core/util.py."""

from core.util import is_all_digits, is_valid_label, parse_int, split, split_whitespace, trim


def test_util_to_str_converts_numbers():
    # The C++ needed its own toStr; Python's str() does the same job.
    assert str(0) == "0"
    assert str(42) == "42"
    assert str(-7) == "-7"


def test_util_parse_int_accepts_whole_numbers():
    assert parse_int("12") == 12
    assert parse_int("  -3 ") == -3


def test_util_parse_int_rejects_bad_text():
    assert parse_int("") is None
    assert parse_int("12a") is None
    assert parse_int("1.5") is None
    assert parse_int("abc") is None
    assert parse_int("99999999999") is None    # does not fit in a 32-bit int
    assert parse_int("1_000") is None          # Python's int() would accept this


def test_util_trim_and_split():
    assert trim("  a b \r\n") == "a b"
    assert trim("   ") == ""
    parts = split("a, b,,c", ",")
    assert len(parts) == 4
    assert parts[1] == "b"
    assert parts[2] == ""
    assert len(split_whitespace("  x \t y\nz ")) == 3
    assert "-".join(split_whitespace("p q")) == "p-q"


def test_util_label_rules():
    assert is_valid_label("a")
    assert is_valid_label("abc_12")
    assert not is_valid_label("")
    assert not is_valid_label("toolong7")
    assert not is_valid_label("a-b")
    assert not is_valid_label("a b")
    assert is_all_digits("0123")
    assert not is_all_digits("12x")
