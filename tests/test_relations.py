"""Relation properties, closures and Warshall's algorithm."""

from conftest import labels_text, pairs_poset
from core.relations import check_properties, compute_closures, equivalence_classes, to_matrix, warshall


def test_relations_reflexive_true_and_false():
    assert check_properties(pairs_poset("1 2", "1>2")).reflexive.holds
    r = check_properties(pairs_poset("1 2", "1>1 1>2", False))
    assert not r.reflexive.holds
    assert r.reflexive.counterexample == "(2,2) is not in R."


def test_relations_symmetric_true_and_false():
    assert check_properties(pairs_poset("1 2", "1>2 2>1")).symmetric.holds
    r = check_properties(pairs_poset("1 2", "1>2"))
    assert not r.symmetric.holds
    assert r.symmetric.counterexample == "(1,2) is in R but (2,1) is not."


def test_relations_antisymmetric_true_and_false():
    assert check_properties(pairs_poset("1 2", "1>2")).antisymmetric.holds
    r = check_properties(pairs_poset("1 2", "1>2 2>1"))
    assert not r.antisymmetric.holds
    assert "(1,2) and (2,1) are both in R" in r.antisymmetric.counterexample


def test_relations_transitive_true_and_false():
    assert check_properties(pairs_poset("1 2 3", "1>2 2>3 1>3")).transitive.holds
    r = check_properties(pairs_poset("1 2 3", "1>2 2>3"))
    assert not r.transitive.holds
    assert r.transitive.counterexample == "(1,2) and (2,3) are in R but (1,3) is not."


def test_relations_equivalence_and_classes():
    p = pairs_poset("1 2 3 4", "1>2 2>1 3>4 4>3")
    assert check_properties(p).is_equivalence
    classes = equivalence_classes(p)
    assert len(classes) == 2
    assert labels_text(p, classes[1]) == "3 4"


def test_relations_warshall_closes_a_chain():
    p = pairs_poset("1 2 3 4", "1>2 2>3 3>4", False)
    steps = []
    closure = warshall(p.R, p.labels, steps)
    assert closure[0][3] == 1          # 1 -> 2 -> 3 -> 4
    assert closure[1][3] == 1
    assert closure[3][0] == 0
    assert len(steps) == 4             # one matrix snapshot per k
    assert "(1,4)" in steps[2].detail or "(1,3)" in steps[1].detail


def test_relations_reflexive_and_symmetric_closures():
    p = pairs_poset("a b", "a>b", False)
    c = compute_closures(p)
    assert c.reflexive[1][1] == 1
    assert c.symmetric[1][0] == 1
    assert c.transitive[1][0] == 0
    assert c.reflexive_transitive[0][0] == 1


def test_relations_empty_set_is_vacuously_everything():
    p = pairs_poset("", "")
    r = check_properties(p)
    assert r.reflexive.holds and r.symmetric.holds and r.antisymmetric.holds and r.transitive.holds
    assert len(to_matrix(p)) == 0
