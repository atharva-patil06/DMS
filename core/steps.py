"""Helpers for writing the "Show Working" step log.

Every analysis function takes an optional `steps` list. These helpers do
nothing when it is None, so callers never need an if-check.
"""

from core.types import Step


def zero_matrix(n):
    """An n x n matrix filled with zeros."""
    return [[0] * n for _ in range(n)]


def copy_matrix(matrix):
    """A separate copy of a matrix, so later changes don't affect it."""
    return [list(row) for row in matrix]


def add_step(steps, title, detail, result):
    """Append a text-only step. result is "OK", "FAIL", "INFO" or "HEAD"."""
    if steps is None:
        return
    steps.append(Step(title, detail, result))


def add_matrix_step(steps, title, detail, matrix):
    """Append a step together with a snapshot (copy) of a 0/1 matrix."""
    if steps is None:
        return
    steps.append(Step(title, detail, "INFO", copy_matrix(matrix)))


def label_of(poset, index):
    """The label of one element, e.g. label_of(p, 0) -> "1"."""
    return poset.labels[index]


def pair_text(poset, a, b):
    """'(a,b)' using the element labels."""
    return "(" + label_of(poset, a) + "," + label_of(poset, b) + ")"


def set_text(poset, indices):
    """'{a, b, c}' using labels; the empty set is written '{ }'."""
    if len(indices) == 0:
        return "{ }"
    return "{" + ", ".join(label_of(poset, i) for i in indices) + "}"
