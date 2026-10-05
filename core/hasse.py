"""The covering relation (transitive reduction) and a level layout for the Hasse diagram."""

from core.poset import longest_chain_ending, require_partial_order, strictly_below
from core.steps import add_step, label_of, pair_text


def _find_middle(poset, a, b):
    """Look for an element c with a < c < b.

    Returns (c or None, tried) where tried is the text "c=2 no, c=3 yes"
    for the Show Working panel.
    """
    tried = ""
    for c in range(poset.size()):
        if c == a or c == b:
            continue
        between = strictly_below(poset, a, c) and strictly_below(poset, c, b)
        tried += ("" if tried == "" else ", ") + "c=" + label_of(poset, c) + (" yes" if between else " no")
        if between:
            return c, tried
    return None, tried


def cover_relation(poset, steps=None):
    """The Hasse diagram's edges (transitive reduction).

    (a,b) is kept iff b covers a: a < b and there is no c with a < c < b.
    An edge implied by transitivity is removed. Returns a list of (a, b).
    """
    require_partial_order(poset, "the Hasse diagram")
    covers = []
    for a in range(poset.size()):
        for b in range(poset.size()):
            if not strictly_below(poset, a, b):
                continue
            middle, tried = _find_middle(poset, a, b)
            question = "Is there c with " + label_of(poset, a) + " < c < " + label_of(poset, b) + "? "
            if middle is not None:
                add_step(steps, "Pair " + pair_text(poset, a, b),
                         question + "Checking " + tried + " -> edge " + pair_text(poset, a, b) +
                         " removed (implied by " + label_of(poset, a) + " < " + label_of(poset, middle) +
                         " < " + label_of(poset, b) + ").", "FAIL")
            else:
                covers.append((a, b))
                checked = "No other elements." if tried == "" else "Checking " + tried + "."
                add_step(steps, "Pair " + pair_text(poset, a, b),
                         question + checked + " Nothing in between, so " + label_of(poset, b) + " covers " +
                         label_of(poset, a) + ": keep edge.", "OK")
    return covers


def hasse_levels(poset):
    """Level of each element for drawing.

    The length of the longest chain from a minimal element up to it, so
    minimal elements are on level 0.
    """
    require_partial_order(poset, "the Hasse levels")
    length, previous = longest_chain_ending(poset)
    return [length[x] - 1 for x in range(poset.size())]
