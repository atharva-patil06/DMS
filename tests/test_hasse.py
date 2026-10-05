"""Covering relation, levels and a randomized cross-check."""

import random

from conftest import pairs_poset, pairs_text, rule_poset
from core.hasse import cover_relation, hasse_levels
from core.relations import compute_closures
from core.steps import zero_matrix
from core.types import MAX_ELEMENTS, Poset


def test_hasse_divisors_of_12():
    p = rule_poset("1 2 3 4 6 12", "divisibility")
    assert pairs_text(p, cover_relation(p)) == "1>2 1>3 2>4 2>6 3>6 4>12 6>12"


def test_hasse_chain_is_a_straight_line():
    p = rule_poset("5 1 3 9", "leq")
    assert pairs_text(p, cover_relation(p)) == "1>3 3>5 5>9"
    levels = hasse_levels(p)
    assert levels[1] == 0     # 1 at the bottom
    assert levels[3] == 3     # 9 at the top


def test_hasse_antichain_has_no_edges():
    p = pairs_poset("a b c", "")
    assert len(cover_relation(p)) == 0
    assert sum(hasse_levels(p)) == 0


def test_hasse_step_log_explains_removed_edges():
    p = rule_poset("1 2 4", "divisibility")
    steps = []
    cover_relation(p, steps)
    explained = False
    for step in steps:
        if "edge (1,4) removed" in step.detail and "c=2 yes" in step.detail:
            explained = True
    assert explained


def test_hasse_levels_of_power_set():
    p = rule_poset("e a b ab", "subset")
    levels = hasse_levels(p)
    assert levels[0] == 0
    assert levels[1] == 1
    assert levels[3] == 2


def naive_covers(p):
    """Brute force straight from the definition, written independently of
    cover_relation(): b covers a iff a < b and no c with a < c < b."""
    result = []
    n = p.size()
    for a in range(n):
        for b in range(n):
            if a == b or p.R[a][b] == 0:
                continue
            between = False
            for c in range(n):
                if c != a and c != b and p.R[a][c] == 1 and p.R[c][b] == 1:
                    between = True
            if not between:
                result.append((a, b))
    return result


def random_test_poset(n, rng):
    """A random poset: random pairs i<j (no cycles possible), then R*."""
    p = Poset([str(i) for i in range(n)], zero_matrix(n))
    for i in range(n):
        for j in range(i + 1, n):
            if rng.randrange(100) < 35:
                p.R[i][j] = 1
    p.R = compute_closures(p).reflexive_transitive
    return p


def test_hasse_randomized_cross_check_against_brute_force():
    rng = random.Random(2024)      # fixed seed: the same 300 posets every run
    for trial in range(300):
        p = random_test_poset(1 + rng.randrange(MAX_ELEMENTS), rng)
        assert pairs_text(p, cover_relation(p)) == pairs_text(p, naive_covers(p))
