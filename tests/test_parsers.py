"""Input parsing and validation."""

import pytest

from conftest import build_error_field, build_error_message, labels_text, pairs_poset, rule_poset
from core.errors import InputError
from core.parsers import (PosetInput, build_poset, divisor_labels, pairs_to_text, parse_elements,
                          parse_matrix, parse_pairs, parse_subset, power_set_labels)


def pairs_input(elements, relation):
    return PosetInput(elements=elements, mode="pairs", relation=relation)


def test_parsers_elements_accept_commas_spaces_and_braces():
    assert " ".join(parse_elements("1,2, 3")) == "1 2 3"
    assert " ".join(parse_elements("{a b ab}")) == "a b ab"
    assert len(parse_elements("")) == 0          # the empty set
    assert len(parse_elements("{}")) == 0


def test_parsers_elements_reject_duplicates_bad_labels_and_too_many():
    assert build_error_field(pairs_input("1,2,2", "")) == "elements"
    assert "listed twice" in build_error_message(pairs_input("1,2,2", ""))
    assert build_error_field(pairs_input("1,a-b", "")) == "elements"
    assert "limit is 12" in build_error_message(pairs_input("1 2 3 4 5 6 7 8 9 10 11 12 13", ""))


def test_parsers_pairs_accept_every_notation():
    labels = parse_elements("1 2 3 4")
    pairs = parse_pairs("(1,2), 1<=3; 2>4 3 <= 4", labels, None, "relation")
    assert pairs == [(0, 1), (0, 2), (1, 3), (2, 3)]
    assert len(parse_pairs("1 ≤ 2", labels, None, "relation")) == 1


def test_parsers_pairs_reject_unknown_elements_and_garbage():
    assert build_error_field(pairs_input("1 2 3", "1>5")) == "relation"
    assert "'5'" in build_error_message(pairs_input("1 2 3", "1>5"))
    assert "Could not read '1-2'" in build_error_message(pairs_input("1 2 3", "1-2"))
    assert "Missing ')'" in build_error_message(pairs_input("1 2 3", "(1,2"))
    assert "exactly two" in build_error_message(pairs_input("1 2 3", "(1,2,3)"))


def test_parsers_duplicate_pairs_are_reported_not_fatal():
    parsed = build_poset(pairs_input("1 2", "1>2, (1,2)"))
    assert len(parsed.notes) == 1
    assert "more than once" in parsed.notes[0]
    assert parsed.poset.related(0, 1)


def test_parsers_matrix_mode():
    m = parse_matrix("110; 0 1 1\n001", 3)
    assert m[0][1] == 1
    assert m[1][2] == 1
    assert m[2][0] == 0
    matrix_input = PosetInput(elements="a b c", mode="matrix", matrix="11;01")
    assert build_error_field(matrix_input) == "matrix"            # not square
    matrix_input.matrix = "110;012;001"
    assert "0 or 1" in build_error_message(matrix_input)


def test_parsers_rules_divisibility_leq_subset():
    div = rule_poset("2 3 6", "divisibility")
    assert div.related(0, 2)          # 2 | 6
    assert not div.related(0, 1)      # 2 does not divide 3
    leq = rule_poset("5 1 3", "leq")
    assert leq.related(1, 0)          # 1 <= 5
    assert not leq.related(0, 2)      # 5 <= 3 is false
    sub = rule_poset("e a ab b", "subset")
    assert sub.related(0, 2)          # empty set is inside ab
    assert sub.related(1, 2)          # a inside ab
    assert not sub.related(1, 3)      # a not inside b


def test_parsers_rules_reject_wrong_labels():
    rule_input = PosetInput(mode="rule", rule="divisibility", elements="1 2 x")
    assert build_error_field(rule_input) == "elements"
    rule_input.elements = "0 1 2"
    assert build_error_field(rule_input) == "elements"           # 0 is not positive
    rule_input.rule = "subset"
    rule_input.elements = "a ab ba"
    assert "same set" in build_error_message(rule_input)
    rule_input.rule = "modulo"
    rule_input.elements = "1 2"
    assert build_error_field(rule_input) == "rule"
    rule_input.mode = "telepathy"
    assert build_error_field(rule_input) == "mode"


def test_parsers_auto_reflexive_is_explained():
    reflexive_input = pairs_input("1 2 3", "1>2")
    reflexive_input.auto_reflexive = True
    parsed = build_poset(reflexive_input)
    assert parsed.poset.related(2, 2)
    assert len(parsed.notes) == 1
    assert "(1,1), (2,2), (3,3)" in parsed.notes[0]


def test_parsers_subsets_and_generated_labels():
    labels = parse_elements("1 2 3")
    assert len(parse_subset("3, 1, 3", labels, "subset")) == 2
    p = pairs_poset("1 2", "1>2")
    assert pairs_to_text(p, True) == "1>2"
    assert pairs_to_text(p, False) == "1>1;1>2;2>2"
    assert " ".join(divisor_labels(12)) == "1 2 3 4 6 12"
    assert " ".join(power_set_labels("ab")) == "e a b ab"
    with pytest.raises(InputError):
        divisor_labels(720)                                       # 720 has 30 divisors
    assert labels_text(p, [1, 0]) == "1 2"
