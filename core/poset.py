"""Partial orders: the axiom check, special elements, bounds, chains and antichains."""

from core.errors import InputError
from core.relations import check_properties, warshall
from core.steps import add_step, label_of, set_text
from core.types import BoundsResult, ChainInfo, PosetVerdict, SpecialElements


def strictly_below(poset, a, b):
    """a < b: a <= b and a != b."""
    return a != b and poset.related(a, b)


def comparable(poset, a, b):
    """a and b are comparable: a <= b or b <= a."""
    return poset.related(a, b) or poset.related(b, a)


def _find_cycle(poset):
    """Explain a cycle between distinct elements, or return "".

    A cycle a -> ... -> b -> ... -> a shows up in the transitive closure as
    both (a,b) and (b,a). No partial order can contain R then.
    """
    closure = warshall(poset.R, poset.labels, None)
    for a in range(poset.size()):
        for b in range(a + 1, poset.size()):
            if closure[a][b] == 1 and closure[b][a] == 1:
                return ("R contains a cycle through " + label_of(poset, a) + " and " + label_of(poset, b) +
                        " (each can be reached from the other), so adding pairs can never make it "
                        "antisymmetric: some pair must be removed.")
    return ""


def _classify_shape(poset, verdict):
    """Fill is_total_order / is_antichain for a relation already known to be a poset."""
    verdict.is_total_order = True
    verdict.is_antichain = True
    for a in range(poset.size()):
        for b in range(a + 1, poset.size()):
            if comparable(poset, a, b):
                verdict.is_antichain = False
            else:
                verdict.is_total_order = False


def is_partial_order(poset, steps=None):
    """Partial order = reflexive + antisymmetric + transitive.

    Reports the first axiom that fails (in that order) with its counterexample.
    Output: a PosetVerdict.
    """
    verdict = PosetVerdict()
    verdict.properties = check_properties(poset, steps)
    pr = verdict.properties
    if not pr.reflexive.holds:
        verdict.failed_axiom = "reflexive"
        verdict.reason = ("Not reflexive: " + pr.reflexive.counterexample +
                          " Tip: tick 'auto-add reflexive pairs' if you meant every (a,a) to be included.")
    elif not pr.antisymmetric.holds:
        verdict.failed_axiom = "antisymmetric"
        verdict.reason = "Not antisymmetric: " + pr.antisymmetric.counterexample
    elif not pr.transitive.holds:
        verdict.failed_axiom = "transitive"
        verdict.reason = "Not transitive: " + pr.transitive.counterexample
    verdict.is_poset = verdict.failed_axiom == ""
    cycle = "" if verdict.is_poset else _find_cycle(poset)
    verdict.has_cycle = cycle != ""
    if verdict.has_cycle:
        verdict.reason += " " + cycle
    if verdict.is_poset:
        _classify_shape(poset, verdict)
    add_step(steps, "Is R a partial order?",
             "Reflexive, antisymmetric and transitive, so (A, <=) is a POSET." if verdict.is_poset else verdict.reason,
             "OK" if verdict.is_poset else "FAIL")
    return verdict


def require_partial_order(poset, what):
    """Raise InputError (field "relation") if R is not a partial order.

    `what` names the thing we wanted to compute, for the message.
    """
    verdict = is_partial_order(poset, None)
    if not verdict.is_poset:
        raise InputError("Cannot compute " + what + " because R is not a partial order. " +
                         verdict.reason, "relation")


def _strictly_below_set(poset, x):
    """Elements strictly below x."""
    return [y for y in range(poset.size()) if strictly_below(poset, y, x)]


def _strictly_above_set(poset, x):
    """Elements strictly above x."""
    return [y for y in range(poset.size()) if strictly_below(poset, x, y)]


def _find_extreme(poset, want_least):
    """The least element (below every element), or with want_least=False the greatest.

    Returns None if there is none (if one exists it is unique, by antisymmetry).
    """
    for x in range(poset.size()):
        ok = True
        for y in range(poset.size()):
            ordered = poset.related(x, y) if want_least else poset.related(y, x)
            if not ordered:
                ok = False
        if ok:
            return x
    return None


def _log_extreme(steps, poset, name, found, candidates):
    if found is not None:
        if name == "least":
            detail = label_of(poset, found) + " <= every element of A, so it is the least element."
        else:
            detail = "Every element of A <= " + label_of(poset, found) + ", so it is the greatest element."
    else:
        detail = ("No element works. There are " + str(candidates) + (" minimal" if name == "least" else " maximal") +
                  " elements; a " + name + " element must be the only one, so none exists.")
    add_step(steps, "Is there a " + name + " element?", detail, "OK" if found is not None else "INFO")


def special_elements(poset, steps=None):
    """Minimal, maximal, least and greatest elements of a poset.

    Minimal: nothing strictly below. Maximal: nothing strictly above.
    Least/greatest: below/above every element (None if it does not exist).
    """
    require_partial_order(poset, "special elements")
    result = SpecialElements()
    for x in range(poset.size()):
        below = _strictly_below_set(poset, x)
        above = _strictly_above_set(poset, x)
        if len(below) == 0:
            result.minimal.append(x)
        if len(above) == 0:
            result.maximal.append(x)
        add_step(steps, "Element " + label_of(poset, x),
                 "Strictly below: " + set_text(poset, below) + ", strictly above: " + set_text(poset, above) +
                 (" -> minimal" if len(below) == 0 else "") + (" -> maximal" if len(above) == 0 else ""), "INFO")
    result.least = _find_extreme(poset, True)
    result.greatest = _find_extreme(poset, False)
    _log_extreme(steps, poset, "least", result.least, len(result.minimal))
    _log_extreme(steps, poset, "greatest", result.greatest, len(result.maximal))
    return result


def _is_bound_of(poset, x, subset, upper):
    """Is x an upper bound (or lower bound) of S? Returns (ok, reasoning text)."""
    ok = True
    reasoning = ""
    for i in range(len(subset)):
        s = subset[i]
        holds = poset.related(s, x) if upper else poset.related(x, s)
        a = label_of(poset, s if upper else x)
        b = label_of(poset, x if upper else s)
        reasoning += (", " if i > 0 else "") + a + "<=" + b + (" yes" if holds else " no")
        if not holds:
            ok = False
    return ok, reasoning


def _extreme_of_set(poset, elements, want_least):
    """The least element of a set T (below all of T), or None. want_least=False: the greatest."""
    for i in range(len(elements)):
        ok = True
        for j in range(len(elements)):
            if want_least:
                ordered = poset.related(elements[i], elements[j])
            else:
                ordered = poset.related(elements[j], elements[i])
            if not ordered:
                ok = False
        if ok:
            return elements[i]
    return None


def _log_best(steps, poset, name, bound_list, best, upper):
    kind = "upper bounds " if upper else "lower bounds "
    if len(bound_list) == 0:
        detail = "There are no " + kind + "at all, so no " + name + "."
    elif best is not None:
        detail = ("The " + kind + set_text(poset, bound_list) + " have " + ("a least" if upper else "a greatest") +
                  " element " + label_of(poset, best) + ", so " + name + " = " + label_of(poset, best) + ".")
    else:
        detail = ("The " + kind + set_text(poset, bound_list) + " have no " + ("least" if upper else "greatest") +
                  " element (some of them are incomparable), so the " + name + " does not exist.")
    add_step(steps, name, detail, "OK" if best is not None else "FAIL")


def bounds(poset, subset, steps=None):
    """Upper and lower bounds of a subset S, and its lub and glb.

    u is an upper bound if s <= u for every s in S; the lub is the least
    upper bound and the glb the greatest lower bound (None if missing).
    """
    require_partial_order(poset, "bounds")
    result = BoundsResult()
    for x in range(poset.size()):
        is_upper, up_why = _is_bound_of(poset, x, subset, True)
        is_lower, low_why = _is_bound_of(poset, x, subset, False)
        if is_upper:
            result.upper_bounds.append(x)
        if is_lower:
            result.lower_bounds.append(x)
        add_step(steps, "Candidate " + label_of(poset, x),
                 "Upper bound? " + ("vacuously yes" if len(subset) == 0 else up_why) +
                 ".  Lower bound? " + ("vacuously yes" if len(subset) == 0 else low_why) + ".", "INFO")
    result.lub = _extreme_of_set(poset, result.upper_bounds, True)     # least of the upper bounds
    result.glb = _extreme_of_set(poset, result.lower_bounds, False)    # greatest of the lower bounds
    _log_best(steps, poset, "lub of " + set_text(poset, subset), result.upper_bounds, result.lub, True)
    _log_best(steps, poset, "glb of " + set_text(poset, subset), result.lower_bounds, result.glb, False)
    return result


def _bottom_up_order(poset):
    """An order where everything below x comes before x.

    If a < b then a has strictly fewer elements below it than b.
    """
    order = []
    for count in range(poset.size()):
        for x in range(poset.size()):
            if len(_strictly_below_set(poset, x)) == count:
                order.append(x)
    return order


def longest_chain_ending(poset):
    """For each element, the number of elements in a longest chain ending at it.

    Dynamic programming in bottom-up order. Returns (length, previous) where
    previous[x] is the element before x on that chain (None if x is minimal).
    """
    length = [1] * poset.size()
    previous = [None] * poset.size()
    order = _bottom_up_order(poset)
    for i in range(len(order)):
        x = order[i]
        for j in range(i):
            y = order[j]        # y was processed already, so length[y] is final
            if strictly_below(poset, y, x) and length[y] + 1 > length[x]:
                length[x] = length[y] + 1
                previous[x] = y
    return length, previous


def _is_antichain(poset, mask):
    """True if no two distinct members of the subset `mask` (a bit mask) are comparable."""
    for a in range(poset.size()):
        for b in range(a + 1, poset.size()):
            both = (mask & (1 << a)) and (mask & (1 << b))
            if both and comparable(poset, a, b):
                return False
    return True


def chains_and_antichains(poset):
    """Height (a longest chain) and width (a largest antichain).

    The width tries every subset (at most 2^12 = 4096), fine for our size limit.
    """
    require_partial_order(poset, "chains and antichains")
    info = ChainInfo()
    length, previous = longest_chain_ending(poset)
    top = None
    for x in range(poset.size()):
        if top is None or length[x] > length[top]:
            top = x
    x = top
    while x is not None:
        info.longest_chain.insert(0, x)
        x = previous[x]
    info.height = len(info.longest_chain)
    for mask in range(1 << poset.size()):
        members = [x for x in range(poset.size()) if mask & (1 << x)]
        if len(members) > info.width and _is_antichain(poset, mask):
            info.width = len(members)
            info.largest_antichain = members
    return info
