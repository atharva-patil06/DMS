"""Properties of a relation R on a finite set A, closures and Warshall's algorithm."""

from core.steps import add_matrix_step, add_step, copy_matrix, label_of, pair_text
from core.types import Closures, PropertyCheck, PropertyReport


def _log_property(steps, name, definition, check):
    """Record the outcome of one property test in the step log."""
    if check.holds:
        detail = definition + "  Holds for every element checked."
    else:
        detail = definition + "  Fails: " + check.counterexample
    add_step(steps, name, detail, "OK" if check.holds else "FAIL")


def _test_reflexive(p):
    """Reflexive: for all a in A, (a,a) in R. Returns the first counterexample."""
    check = PropertyCheck()
    for a in range(p.size()):
        if not p.related(a, a):
            check.holds = False
            check.counterexample = pair_text(p, a, a) + " is not in R."
            return check
    return check


def _test_symmetric(p):
    """Symmetric: (a,b) in R implies (b,a) in R."""
    check = PropertyCheck()
    for a in range(p.size()):
        for b in range(p.size()):
            if p.related(a, b) and not p.related(b, a):
                check.holds = False
                check.counterexample = pair_text(p, a, b) + " is in R but " + pair_text(p, b, a) + " is not."
                return check
    return check


def _test_antisymmetric(p):
    """Antisymmetric: (a,b) in R and (b,a) in R imply a = b."""
    check = PropertyCheck()
    for a in range(p.size()):
        for b in range(a + 1, p.size()):
            if p.related(a, b) and p.related(b, a):
                check.holds = False
                check.counterexample = (pair_text(p, a, b) + " and " + pair_text(p, b, a) +
                                        " are both in R, but " + label_of(p, a) + " != " + label_of(p, b) + ".")
                return check
    return check


def _test_transitive(p):
    """Transitive: (a,b) in R and (b,c) in R imply (a,c) in R."""
    check = PropertyCheck()
    for a in range(p.size()):
        for b in range(p.size()):
            if not p.related(a, b):
                continue
            for c in range(p.size()):
                if p.related(b, c) and not p.related(a, c):
                    check.holds = False
                    check.counterexample = (pair_text(p, a, b) + " and " + pair_text(p, b, c) +
                                            " are in R but " + pair_text(p, a, c) + " is not.")
                    return check
    return check


def check_properties(poset, steps=None):
    """Test the four basic properties and record the first counterexample of each.

    Input: a Poset (any relation). Output: a PropertyReport.
    """
    report = PropertyReport()
    report.reflexive = _test_reflexive(poset)
    report.symmetric = _test_symmetric(poset)
    report.antisymmetric = _test_antisymmetric(poset)
    report.transitive = _test_transitive(poset)
    report.is_equivalence = report.reflexive.holds and report.symmetric.holds and report.transitive.holds

    _log_property(steps, "Reflexive?", "Definition: for all a in A, (a,a) in R.", report.reflexive)
    _log_property(steps, "Symmetric?", "Definition: (a,b) in R => (b,a) in R.", report.symmetric)
    _log_property(steps, "Antisymmetric?", "Definition: (a,b) in R and (b,a) in R => a = b.", report.antisymmetric)
    _log_property(steps, "Transitive?", "Definition: (a,b) in R and (b,c) in R => (a,c) in R.", report.transitive)
    if report.is_equivalence:
        add_step(steps, "Equivalence relation", "R is reflexive, symmetric and transitive, "
                 "so it is an equivalence relation and splits A into classes.", "INFO")
    return report


def _new_pairs_text(before, after, labels):
    """List the pairs that are 1 in `after` but 0 in `before`, e.g. "(1,3), (1,4)"."""
    added = []
    for i in range(len(after)):
        for j in range(len(after)):
            if after[i][j] == 1 and before[i][j] == 0:
                added.append("(" + labels[i] + "," + labels[j] + ")")
    if len(added) == 0:
        return "no new pairs"
    return "new pairs " + ", ".join(added)


def warshall(start, labels, steps=None):
    """Warshall's algorithm: the transitive closure R+ of a 0/1 matrix.

    After step k, W[i][j] = 1 iff there is a path from i to j whose middle
    elements all lie in {a0..ak}. So after the last k we have R+.
    `labels` is only used for the step log.
    """
    w = copy_matrix(start)
    n = len(w)
    for k in range(n):
        before = copy_matrix(w)
        for i in range(n):
            for j in range(n):
                if w[i][k] == 1 and w[k][j] == 1:
                    w[i][j] = 1          # path i -> k -> j
        if steps is not None:
            add_matrix_step(steps, "Warshall step k = " + labels[k],
                            "W[i][j] = W[i][j] OR (W[i][k] AND W[k][j]) using " + labels[k] +
                            " as a middle element: " + _new_pairs_text(before, w, labels) + ".", w)
    return w


def compute_closures(poset, steps=None):
    """Reflexive, symmetric and transitive closures (Warshall), plus R*.

    R* is the transitive closure of the reflexive closure: the smallest
    reflexive and transitive relation containing R.
    """
    n = poset.size()
    closures = Closures()
    closures.reflexive = copy_matrix(poset.R)
    closures.symmetric = copy_matrix(poset.R)
    for i in range(n):
        closures.reflexive[i][i] = 1                     # add (a,a)
        for j in range(n):
            if poset.related(i, j):
                closures.symmetric[j][i] = 1             # add (b,a)
    add_matrix_step(steps, "Reflexive closure", "R union {(a,a) : a in A}.", closures.reflexive)
    add_matrix_step(steps, "Symmetric closure", "R union R^-1, i.e. add (b,a) for every (a,b).", closures.symmetric)
    add_step(steps, "Transitive closure (Warshall)",
             "Start from W = M(R); for each k in turn, allow paths through element k.", "INFO")
    closures.transitive = warshall(poset.R, poset.labels, steps)
    closures.reflexive_transitive = warshall(closures.reflexive, poset.labels, None)
    return closures


def to_matrix(poset):
    """The 0/1 relation matrix of the poset (a copy)."""
    return copy_matrix(poset.R)


def equivalence_classes(poset):
    """For an equivalence relation: the classes [a] = {b : a R b}, as index lists."""
    classes = []
    assigned = [False] * poset.size()
    for a in range(poset.size()):
        if assigned[a]:
            continue
        cls = []
        for b in range(poset.size()):
            if poset.related(a, b):
                cls.append(b)
                assigned[b] = True
        classes.append(cls)
    return classes
