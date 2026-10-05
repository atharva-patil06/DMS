"""Random posets for the Boss level and the "Generate" buttons.

The output is plain input text (elements + rule or pairs), so a generated
poset goes through exactly the same parser as anything a user types.
"""

import random

from core.errors import InputError
from core.parsers import PosetInput, divisor_labels, pairs_to_text
from core.relations import compute_closures
from core.steps import zero_matrix
from core.types import MAX_ELEMENTS, Poset


class GeneratedPoset:
    """A generated poset: its type, a title, and the input to build it from."""

    def __init__(self, title, poset_input):
        self.type = ""
        self.title = title
        self.input = poset_input


def random_int(low, high):
    """Random whole number in [low, high]."""
    return random.randint(low, high)


def count_divisors(n):
    """Number of positive divisors of n."""
    count = 0
    for d in range(1, n + 1):
        if n % d == 0:
            count += 1
    return count


def _divisibility_poset(size):
    """Divisors of a random n that has exactly `size` divisors.

    Searching n <= 2000 always finds one for 1..12 (e.g. 11 divisors -> n = 1024).
    """
    candidates = [n for n in range(1, 2001) if count_divisors(n) == size]
    n = candidates[random_int(0, len(candidates) - 1)]
    return GeneratedPoset("Divisors of " + str(n),
                          PosetInput(elements=" ".join(divisor_labels(n)), mode="rule", rule="divisibility"))


def _shuffle(items):
    """Shuffle a list in place (Fisher-Yates)."""
    for i in range(len(items) - 1, 0, -1):
        j = random_int(0, i)
        items[i], items[j] = items[j], items[i]


def _subset_poset(size):
    """`size` different subsets of {a,b,c,d}, ordered by inclusion."""
    masks = list(range(16))
    _shuffle(masks)
    labels = []
    for i in range(size):
        label = ""
        for bit in range(4):
            if masks[i] & (1 << bit):
                label += "abcd"[bit]
        labels.append(label if label != "" else "e")
    return GeneratedPoset("Some subsets of {a,b,c,d}",
                          PosetInput(elements=" ".join(labels), mode="rule", rule="subset"))


def _leq_poset(size):
    """`size` distinct numbers from 1..50 under <= (always a chain)."""
    labels = []
    while len(labels) < size:
        label = str(random_int(1, 50))
        if label not in labels:
            labels.append(label)
    return GeneratedPoset("Numbers under <=", PosetInput(elements=" ".join(labels), mode="rule", rule="leq"))


def _random_poset(size):
    """A general poset.

    Shuffle the elements, add random "upward" pairs only from earlier to later
    elements (so there can be no cycle), then take the reflexive-transitive
    closure so the result is a partial order.
    """
    order = list(range(size))
    _shuffle(order)
    p = Poset(["abcdefghijkl"[i] for i in range(size)], zero_matrix(size))
    for i in range(size):
        for j in range(i + 1, size):
            if random_int(1, 100) <= 30:
                p.R[order[i]][order[j]] = 1
    p.R = compute_closures(p).reflexive_transitive
    return GeneratedPoset("A random poset",
                          PosetInput(elements=" ".join(p.labels), mode="pairs",
                                     relation=pairs_to_text(p, True), auto_reflexive=True))


def generate_poset(poset_type, size):
    """A random poset. poset_type: divisibility, subset, leq or random; size 1..12."""
    if size < 1 or size > MAX_ELEMENTS:
        raise InputError("Size must be between 1 and " + str(MAX_ELEMENTS) + ".", "size")
    makers = {"divisibility": _divisibility_poset, "subset": _subset_poset,
              "leq": _leq_poset, "random": _random_poset}
    if poset_type not in makers:
        raise InputError("Unknown generator type '" + poset_type + "'. Use divisibility, subset, leq or random.", "type")
    generated = makers[poset_type](size)
    generated.type = poset_type
    return generated
