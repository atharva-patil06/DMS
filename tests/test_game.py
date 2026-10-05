"""Scoring, feedback, level loading and generators, called directly (no network)."""

import pytest

from conftest import LEVELS_DIR, pairs_poset, rule_poset
from app.game import (GameSession, check_boss_answer, check_bounds_answer, check_fix_relation, check_hasse_edges, check_lattice_answer,
                      check_spot_elements, compute_score, compute_stars)
from app.generators import generate_poset
from app.level_loader import LevelFileError, load_levels, parse_levels
from core.errors import InputError
from core.parsers import build_poset, parse_subset
from core.poset import is_partial_order


def has_kind(result, kind):
    return any(f.kind == kind for f in result.feedback)


def two_levels():
    return parse_levels("id: 1\ntype: build_hasse\ntitle: A\nelements: 1 2 4\nrule: divisibility\npoints: 100\n\n"
                        "id: 2\ntype: spot_elements\ntitle: B\nelements: 1 2 3\nrule: divisibility\npoints: 50\n"
                        "unlock_after: 1\n", "inline")


# Regression test required by the spec: a redundant transitive edge is WRONG.
def test_game_redundant_transitive_edge_is_judged_wrong():
    p = rule_poset("1 2 4", "divisibility")
    r = check_hasse_edges(p, "1>2;2>4;1>4")
    assert r.correct_edges == 2
    assert r.wrong_edges == 1
    assert has_kind(r, "redundant")
    assert r.accuracy < 1.0
    assert any("1 < 2 < 4 already forces it" in f.message for f in r.feedback)


def test_game_hasse_feedback_kinds():
    p = rule_poset("1 2 3 6", "divisibility")
    r = check_hasse_edges(p, "2>1;2>3;1>3")
    assert has_kind(r, "downward")      # 2>1 drawn upside down
    assert has_kind(r, "unrelated")     # 2 and 3 are not related
    assert has_kind(r, "missing")       # 2-6 and 3-6 missing
    assert has_kind(r, "correct")       # 1-3 is right


def test_game_hasse_perfect_and_partial_scores():
    p = rule_poset("1 2 3 6", "divisibility")
    perfect = check_hasse_edges(p, "1>2;1>3;2>6;3>6")
    assert perfect.accuracy > 0.999
    assert perfect.precision == 1.0
    assert perfect.recall == 1.0
    half = check_hasse_edges(p, "1>2;1>3")
    assert half.recall == 0.5
    assert half.precision == 1.0
    assert half.accuracy == 0.5


def test_game_spot_elements_answers():
    p = rule_poset("2 3 4 6 9 12 18", "divisibility")
    assert check_spot_elements(p, "minimal:2,3;maximal:12,18;least:none;greatest:none").accuracy > 0.999
    wrong = check_spot_elements(p, "minimal:2,4;maximal:12,18;least:2;greatest:none")
    assert wrong.accuracy < 0.75
    assert has_kind(wrong, "wrong")
    assert has_kind(wrong, "missing")


def test_game_bounds_answers():
    p = rule_poset("1 2 3 4 6 9 12 18 36", "divisibility")
    s = parse_subset("4 6", p.labels, "subset")
    assert check_bounds_answer(p, s, "upper:12,36;lower:1,2;lub:12;glb:2").accuracy > 0.999
    r = check_bounds_answer(p, s, "upper:12,36,18;lower:1,2;lub:36;glb:2")
    assert r.accuracy < 1.0
    assert has_kind(r, "wrong")


def test_game_fix_relation_answers():
    original = pairs_poset("1 2 3", "1>2 2>3", False)
    assert check_fix_relation(original, "1>1;2>2;3>3;1>2;2>3;1>3").accuracy > 0.999
    extra = check_fix_relation(original, "1>1;2>2;3>3;1>2;2>3;1>3;3>1")
    assert has_kind(extra, "extra")
    assert extra.accuracy < 1.0
    removed = check_fix_relation(original, "1>1;2>2;3>3;1>2")
    assert has_kind(removed, "wrong")
    assert has_kind(removed, "missing")


def test_game_lattice_answers():
    n = pairs_poset("a b c d", "a>c b>c b>d")
    assert check_lattice_answer(n, "lattice:no;pair:a,b").accuracy > 0.999
    assert check_lattice_answer(n, "lattice:no;pair:b,c").accuracy == 0.5    # right verdict, wrong pair
    assert check_lattice_answer(n, "lattice:yes").accuracy == 0.0
    d30 = rule_poset("1 2 3 5 6 10 15 30", "divisibility")
    assert check_lattice_answer(d30, "lattice:yes").accuracy > 0.999


def test_game_boss_answer_mixes_tasks():
    p = rule_poset("1 2 3 6", "divisibility")
    assert check_boss_answer(p, "edges:1>2,1>3,2>6,3>6;minimal:1;maximal:6;lattice:yes").accuracy > 0.999
    partial = check_boss_answer(p, "edges:1>2,1>3,2>6,3>6;minimal:1;maximal:6;lattice:no").accuracy
    assert 0.74 < partial < 0.76


def test_game_scores_and_stars():
    assert compute_score(100, 1.0, 0, 1) == 100
    assert compute_score(100, 1.0, 1, 1) == 85      # one hint costs 15%
    assert compute_score(100, 1.0, 0, 3) == 90      # two extra attempts cost 10%
    assert compute_score(100, 0.1, 2, 1) == 0       # never negative
    assert compute_score(150, 0.25, 1, 2) == 8      # 37.5 - 22.5 - 7.5 = 7.5 rounds up (the old C++ build gave 7)
    assert compute_stars(1.0, 0, 1) == 3
    assert compute_stars(1.0, 1, 2) == 2
    assert compute_stars(1.0, 2, 3) == 1
    assert compute_stars(0.9, 0, 1) == 0


def test_game_session_unlocks_and_hints():
    game = GameSession(two_levels())
    assert game.is_unlocked(1)
    assert not game.is_unlocked(2)
    failed = game.check_level(1, "1>4")
    assert not failed.passed
    assert not game.is_unlocked(2)
    h1 = game.hint(1)
    assert h1.number == 1
    assert "{1}" in h1.text
    h2 = game.hint(1)
    assert "Draw 1-2" in h2.text
    assert game.hint(1).number == 0                  # only two hints
    ok = game.check_level(1, "1>2;2>4")
    assert ok.passed
    assert ok.score == 100 - 30 - 5                  # two hints + one extra attempt
    assert ok.newly_unlocked == [2]
    assert game.is_unlocked(2)
    assert game.total_score() == 65
    assert len(game.history) == 2


def test_game_level_loader_rejects_malformed_files():
    with pytest.raises(LevelFileError) as caught:
        parse_levels("id: 1\ntype: dance\ntitle: x\nelements: 1\nrule: leq\npoints: 5\n", "bad.txt")
    assert "unknown level type 'dance'" in str(caught.value)
    with pytest.raises(LevelFileError) as caught:
        parse_levels("id: 1\nthis line has no colon\n", "bad.txt")
    assert "bad.txt line 2" in str(caught.value)
    with pytest.raises(LevelFileError) as caught:
        parse_levels("id: one\n", "bad.txt")
    assert "whole number" in str(caught.value)


def test_game_real_level_files_load_and_validate():
    levels = load_levels(LEVELS_DIR)
    assert len(levels) >= 6
    seen = set(level.type for level in levels)
    for level_type in ["build_hasse", "spot_elements", "bounds", "fix_relation", "lattice", "boss"]:
        assert level_type in seen


def test_game_generators_produce_valid_posets():
    for poset_type in ["divisibility", "subset", "leq", "random"]:
        for size in range(1, 13):
            p = build_poset(generate_poset(poset_type, size).input).poset
            assert p.size() == size
            assert is_partial_order(p).is_poset
    with pytest.raises(InputError):
        generate_poset("random", 13)
