"""Partial order check, special elements, bounds, chains."""

import pytest

from conftest import labels_text, pairs_poset, rule_poset
from core.errors import InputError
from core.parsers import parse_subset
from core.poset import bounds, chains_and_antichains, is_partial_order, special_elements


def test_poset_reports_each_failed_axiom():
    assert is_partial_order(pairs_poset("1 2", "1>2", False)).failed_axiom == "reflexive"
    assert is_partial_order(pairs_poset("1 2", "1>2 2>1")).failed_axiom == "antisymmetric"
    assert is_partial_order(pairs_poset("1 2 3", "1>2 2>3")).failed_axiom == "transitive"
    ok = is_partial_order(rule_poset("1 2 3 6", "divisibility"))
    assert ok.is_poset
    assert ok.failed_axiom == ""


def test_poset_reflexive_failure_suggests_auto_add():
    v = is_partial_order(pairs_poset("1 2", "1>2", False))
    assert "auto-add reflexive pairs" in v.reason


def test_poset_detects_cycles():
    v = is_partial_order(pairs_poset("1 2 3", "1>2 2>3 3>1"))
    assert not v.is_poset
    assert v.has_cycle
    assert "cycle" in v.reason


def test_poset_total_order_and_antichain_shapes():
    chain = is_partial_order(rule_poset("1 2 4 8", "divisibility"))
    assert chain.is_total_order
    assert not chain.is_antichain
    flat = is_partial_order(pairs_poset("a b c", ""))
    assert flat.is_antichain
    assert not flat.is_total_order


def test_poset_special_elements_with_no_least_or_greatest():
    p = rule_poset("2 3 4 6 9 12 18", "divisibility")
    se = special_elements(p)
    assert labels_text(p, se.minimal) == "2 3"
    assert labels_text(p, se.maximal) == "12 18"
    assert se.least is None
    assert se.greatest is None


def test_poset_special_elements_with_least_and_greatest():
    p = rule_poset("1 2 3 6", "divisibility")
    steps = []
    se = special_elements(p, steps)
    assert p.labels[se.least] == "1"
    assert p.labels[se.greatest] == "6"
    assert len(steps) >= 6


def test_poset_bounds_lub_and_glb():
    p = rule_poset("1 2 3 4 6 9 12 18 36", "divisibility")
    b = bounds(p, parse_subset("4 6", p.labels, "subset"))
    assert labels_text(p, b.upper_bounds) == "12 36"
    assert labels_text(p, b.lower_bounds) == "1 2"
    assert p.labels[b.lub] == "12"
    assert p.labels[b.glb] == "2"


def test_poset_bounds_without_lub():
    p = pairs_poset("a b c d t", "a>c a>d b>c b>d c>t d>t a>t b>t")
    steps = []
    b = bounds(p, parse_subset("a b", p.labels, "subset"), steps)
    assert labels_text(p, b.upper_bounds) == "c d t"
    assert b.lub is None
    assert len(b.lower_bounds) == 0
    assert b.glb is None
    assert "no least" in steps[-2].detail


def test_poset_height_and_width():
    p = rule_poset("1 2 3 4 6 12", "divisibility")
    info = chains_and_antichains(p)
    assert info.height == 4                 # e.g. 1 | 2 | 4 | 12
    assert info.width == 2                  # e.g. {2, 3}
    assert len(info.longest_chain) == 4
    flat = pairs_poset("a b c", "")
    assert chains_and_antichains(flat).width == 3
    assert chains_and_antichains(flat).height == 1


def test_poset_functions_refuse_non_posets():
    with pytest.raises(InputError) as caught:
        special_elements(pairs_poset("1 2", "1>2 2>1"))
    assert caught.value.field == "relation"
    assert "not a partial order" in caught.value.message


def test_poset_single_element():
    p = pairs_poset("x", "")
    se = special_elements(p)
    assert se.least == 0
    assert se.greatest == 0
    assert is_partial_order(p).is_total_order
