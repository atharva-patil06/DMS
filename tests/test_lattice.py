"""lub/glb tables and the lattice test."""

from conftest import pairs_poset, rule_poset
from core.lattice import is_failing_pair, lattice_check


def test_lattice_divisors_of_30_is_a_lattice():
    p = rule_poset("1 2 3 5 6 10 15 30", "divisibility")
    r = lattice_check(p)
    assert r.is_lattice
    assert p.labels[r.join_table[1][2]] == "6"     # lub(2,3) = lcm = 6
    assert p.labels[r.meet_table[4][5]] == "2"     # glb(6,10) = gcd = 2


def test_lattice_n_shape_is_not_a_lattice():
    p = pairs_poset("a b c d", "a>c b>c b>d")
    steps = []
    r = lattice_check(p, steps)
    assert not r.is_lattice
    assert is_failing_pair(r, 0, 1)                # {a,b} has no glb
    assert "{a,b}" in r.reason
    assert steps[-1].result == "FAIL"


def test_lattice_two_incomparable_upper_bounds():
    p = rule_poset("1 2 3 12 18 36", "divisibility")
    r = lattice_check(p)
    assert not r.is_lattice
    assert r.fail_kind == "lub"
    assert "{2,3} has upper bounds {12, 18, 36} but no least one" in r.reason


def test_lattice_chain_and_single_element_are_lattices():
    assert lattice_check(rule_poset("4 2 9", "leq")).is_lattice    # every chain is a lattice
    assert lattice_check(pairs_poset("x", "")).is_lattice


def test_lattice_two_maximal_elements_fail():
    r = lattice_check(pairs_poset("a b c", "a>b a>c"))
    assert not r.is_lattice
    assert "no upper bound at all" in r.reason


def test_lattice_empty_poset_is_vacuous():
    steps = []
    r = lattice_check(pairs_poset("", ""), steps)
    assert r.is_lattice
    assert "vacuously" in steps[-1].detail
