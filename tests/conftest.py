"""Small helpers shared by the test files (pytest loads this file automatically)."""

import os

from core.errors import InputError
from core.parsers import PosetInput, build_poset

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LEVELS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "levels")


def pairs_poset(elements, pairs, auto_reflexive=True):
    """A poset from elements + pair text, e.g. pairs_poset("1 2 3", "1>2 2>3")."""
    return build_poset(PosetInput(elements=elements, mode="pairs", relation=pairs,
                                  auto_reflexive=auto_reflexive)).poset


def rule_poset(elements, rule):
    """A poset from a rule, e.g. rule_poset("1 2 3 6", "divisibility")."""
    return build_poset(PosetInput(elements=elements, mode="rule", rule=rule)).poset


def sorted_words(text):
    """Sort space-separated words so set comparisons ignore order."""
    return " ".join(sorted(text.split()))


def labels_text(poset, indices):
    """'1 2 3' for a list of indices (sorted)."""
    return sorted_words(" ".join(poset.labels[i] for i in indices))


def pairs_text(poset, pairs):
    """'a>b c>d' for a list of pairs (sorted)."""
    return sorted_words(" ".join(poset.labels[a] + ">" + poset.labels[b] for (a, b) in pairs))


def build_error_field(poset_input):
    """Run build_poset and return the InputError's field ("" if no error)."""
    try:
        build_poset(poset_input)
    except InputError as error:
        return error.field
    return ""


def build_error_message(poset_input):
    """Same, but return the error message."""
    try:
        build_poset(poset_input)
    except InputError as error:
        return error.message
    return ""
