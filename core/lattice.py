"""lub/glb tables and the lattice test.

A lattice is a poset in which every pair {a,b} has both a lub and a glb.
"""

from core.poset import bounds, require_partial_order
from core.steps import add_step, label_of, set_text
from core.types import LatticeReport


def _missing_reason(poset, a, b, bound_list, upper):
    """Explain why one bound is missing, e.g. "{b,c} has upper bounds {d, e} but no least one"."""
    pair_set = "{" + label_of(poset, a) + "," + label_of(poset, b) + "}"
    kind = "upper" if upper else "lower"
    best = "lub" if upper else "glb"
    if len(bound_list) == 0:
        return pair_set + " has no " + kind + " bound at all, so its " + best + " does not exist."
    return (pair_set + " has " + kind + " bounds " + set_text(poset, bound_list) + " but no " +
            ("least" if upper else "greatest") + " one, so its " + best + " does not exist.")


def _record_failure(report, a, b, kind, reason):
    """Record the first failing pair found."""
    if report.fail_a is not None:
        return
    report.fail_a = a
    report.fail_b = b
    report.fail_kind = kind
    report.reason = reason


def _bound_text(poset, index):
    return label_of(poset, index) if index is not None else "none"


def _final_step(steps, report, n):
    if not report.is_lattice:
        detail = "Not a lattice: " + report.reason
    elif n == 0:
        detail = ("The empty poset has no pairs, so it is a lattice vacuously "
                  "(some textbooks require a lattice to be non-empty).")
    else:
        detail = "Every pair has a lub and a glb, so (A, <=) is a lattice."
    add_step(steps, "Lattice?", detail, "OK" if report.is_lattice else "FAIL")


def lattice_check(poset, steps=None):
    """Build the full join (lub) and meet (glb) tables and test for a lattice.

    If it is not a lattice, the report names the first failing pair and why.
    """
    require_partial_order(poset, "the lattice test")
    n = poset.size()
    report = LatticeReport()
    report.join_table = [[None] * n for _ in range(n)]
    report.meet_table = [[None] * n for _ in range(n)]
    for a in range(n):
        for b in range(a, n):
            br = bounds(poset, [a, b], None)
            report.join_table[a][b] = report.join_table[b][a] = br.lub
            report.meet_table[a][b] = report.meet_table[b][a] = br.glb
            if br.lub is None:
                _record_failure(report, a, b, "lub", _missing_reason(poset, a, b, br.upper_bounds, True))
            if br.glb is None:
                _record_failure(report, a, b, "glb", _missing_reason(poset, a, b, br.lower_bounds, False))
            if a == b:
                continue        # lub(a,a) = glb(a,a) = a: not worth a log line
            add_step(steps, "{" + label_of(poset, a) + "," + label_of(poset, b) + "}",
                     "Upper bounds " + set_text(poset, br.upper_bounds) + " -> lub = " + _bound_text(poset, br.lub) +
                     ";  lower bounds " + set_text(poset, br.lower_bounds) + " -> glb = " + _bound_text(poset, br.glb),
                     "OK" if (br.lub is not None and br.glb is not None) else "FAIL")
    report.is_lattice = report.fail_a is None
    _final_step(steps, report, n)
    return report


def is_failing_pair(report, a, b):
    """True if {a,b} has no lub or no glb according to the report's tables."""
    return report.join_table[a][b] is None or report.meet_table[a][b] is None
