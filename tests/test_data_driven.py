"""Loops over the "key: value" blocks in tests/data/*.txt (the same files the C++ used).

Each block describes one input and the answers we expect from the core.
"""

import os

from conftest import DATA_DIR, labels_text, pairs_text, sorted_words
from app.game import check_hasse_edges, compute_score
from core.errors import InputError
from core.hasse import cover_relation
from core.lattice import lattice_check
from core.parsers import PosetInput, build_poset
from core.poset import chains_and_antichains, is_partial_order, special_elements


def read_blocks(file_name):
    """Read a file of blocks separated by blank lines ('#' lines are comments)."""
    blocks = []
    current = {}
    with open(os.path.join(DATA_DIR, file_name), encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip(" \t\r\n")
            if line == "":
                if current:
                    blocks.append(current)
                current = {}
            elif line[0] != "#":
                colon = line.find(":")
                if colon < 0:
                    current[line] = ""
                else:
                    current[line[:colon].strip()] = line[colon + 1:].strip()
    if current:
        blocks.append(current)
    return blocks


def block_input(block):
    poset_input = PosetInput(elements=block.get("elements", ""),
                             auto_reflexive=block.get("auto_reflexive") == "yes")
    if "rule" in block:
        poset_input.mode = "rule"
        poset_input.rule = block["rule"]
    elif "matrix" in block:
        poset_input.mode = "matrix"
        poset_input.matrix = block["matrix"]
    else:
        poset_input.mode = "pairs"
        poset_input.relation = block.get("relation", "")
    return poset_input


def yes_no(value):
    return "yes" if value else "no"


def labels_or_none(p, indices):
    return "none" if len(indices) == 0 else labels_text(p, indices)


def expect(block, key, actual, failures):
    """Compare one expectation (word order ignored); record a failure message."""
    if key in block and sorted_words(block[key]) != sorted_words(actual):
        failures.append("[" + block.get("name", "?") + "] " + key + ": expected '" + block[key] +
                        "' but got '" + actual + "'")


def check_poset_expectations(block, p, failures):
    v = is_partial_order(p)
    expect(block, "expect_poset", yes_no(v.is_poset), failures)
    expect(block, "expect_failed_axiom", v.failed_axiom if v.failed_axiom else "none", failures)
    expect(block, "expect_reflexive", yes_no(v.properties.reflexive.holds), failures)
    expect(block, "expect_symmetric", yes_no(v.properties.symmetric.holds), failures)
    expect(block, "expect_antisymmetric", yes_no(v.properties.antisymmetric.holds), failures)
    expect(block, "expect_transitive", yes_no(v.properties.transitive.holds), failures)
    expect(block, "expect_equivalence", yes_no(v.properties.is_equivalence), failures)
    expect(block, "expect_cycle", yes_no(v.has_cycle), failures)
    if not v.is_poset:
        return
    expect(block, "expect_total", yes_no(v.is_total_order), failures)
    covers = cover_relation(p)
    expect(block, "expect_cover", "none" if len(covers) == 0 else pairs_text(p, covers), failures)
    se = special_elements(p)
    expect(block, "expect_minimal", labels_or_none(p, se.minimal), failures)
    expect(block, "expect_maximal", labels_or_none(p, se.maximal), failures)
    expect(block, "expect_least", "none" if se.least is None else p.labels[se.least], failures)
    expect(block, "expect_greatest", "none" if se.greatest is None else p.labels[se.greatest], failures)
    expect(block, "expect_lattice", yes_no(lattice_check(p).is_lattice), failures)
    chains = chains_and_antichains(p)
    expect(block, "expect_height", str(chains.height), failures)
    expect(block, "expect_width", str(chains.width), failures)


def test_data_driven_posets():
    blocks = read_blocks("posets.txt")
    assert len(blocks) >= 20
    failures = []
    for block in blocks:
        try:
            p = build_poset(block_input(block)).poset
            expect(block, "expect_error", "none", failures)
            check_poset_expectations(block, p, failures)
        except InputError as error:
            if "expect_error" in block:
                expect(block, "expect_error", error.field, failures)
            else:
                failures.append("[" + block.get("name", "?") + "] unexpected error: " + error.message)
    assert failures == []


def feedback_kinds(result):
    """The distinct feedback kinds in order, e.g. "correct missing redundant"."""
    kinds = []
    for f in result.feedback:
        if f.kind not in kinds:
            kinds.append(f.kind)
    return " ".join(kinds)


def test_data_driven_hasse_checks():
    blocks = read_blocks("hasse_checks.txt")
    assert len(blocks) >= 8
    failures = []
    for block in blocks:
        p = build_poset(block_input(block)).poset
        r = check_hasse_edges(p, block.get("edges", ""))
        expect(block, "expect_correct", str(r.correct_edges), failures)
        expect(block, "expect_wrong", str(r.wrong_edges), failures)
        expect(block, "expect_missing", str(r.missing_edges), failures)
        expect(block, "expect_kinds", feedback_kinds(r), failures)
        expect(block, "expect_accuracy", str(int(r.accuracy * 100 + 0.5)), failures)
        expect(block, "expect_score", str(compute_score(100, r.accuracy, 0, 1)), failures)
    assert failures == []
