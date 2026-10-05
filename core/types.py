"""The plain data classes shared by the whole math core.

A relation R on A = {a0, ..., a(n-1)} is stored as a 0/1 matrix (a list of
lists of int): R[i][j] == 1 exactly when (ai, aj) is in R. Elements are
stored by index; labels are only used for input and output. A pair of
element indices is a tuple (i, j). "No such element" is None.
"""

# The largest set we accept: keeps the brute-force width search and the
# on-screen diagram readable.
MAX_ELEMENTS = 12


class Poset:
    """A finite set A (its labels) together with a relation R on it."""

    def __init__(self, labels=None, R=None):
        self.labels = labels if labels is not None else []
        self.R = R if R is not None else []

    def size(self):
        """Number of elements |A|."""
        return len(self.labels)

    def related(self, a, b):
        """True when (a, b) is in R."""
        return self.R[a][b] == 1


class Step:
    """One line of the "Show Working" panel. result is OK, FAIL, INFO or HEAD."""

    def __init__(self, title, detail, result, matrix=None):
        self.title = title
        self.detail = detail
        self.result = result
        self.matrix = matrix if matrix is not None else []


class PropertyCheck:
    """Whether one property holds, plus a counterexample in words if it fails."""

    def __init__(self):
        self.holds = True
        self.counterexample = ""


class PropertyReport:
    """The four basic properties of a relation."""

    def __init__(self):
        self.reflexive = PropertyCheck()
        self.symmetric = PropertyCheck()
        self.antisymmetric = PropertyCheck()
        self.transitive = PropertyCheck()
        self.is_equivalence = False      # reflexive + symmetric + transitive


class Closures:
    """Reflexive, symmetric, transitive (Warshall) and reflexive-transitive closures."""

    def __init__(self):
        self.reflexive = []
        self.symmetric = []
        self.transitive = []
        self.reflexive_transitive = []


class PosetVerdict:
    """Result of the partial order test."""

    def __init__(self):
        self.is_poset = False
        self.failed_axiom = ""           # "", "reflexive", "antisymmetric" or "transitive"
        self.reason = ""                 # the counterexample in words, plus a tip
        self.has_cycle = False           # R+ links two distinct elements both ways
        self.is_total_order = False      # every two elements comparable
        self.is_antichain = False        # only the pairs (a,a)
        self.properties = PropertyReport()


class SpecialElements:
    """Minimal and maximal elements, and the least/greatest element (or None)."""

    def __init__(self):
        self.minimal = []                # nothing strictly below
        self.maximal = []                # nothing strictly above
        self.least = None                # below everything
        self.greatest = None             # above everything


class BoundsResult:
    """Upper and lower bounds of a subset S, and its lub/glb (or None)."""

    def __init__(self):
        self.upper_bounds = []
        self.lower_bounds = []
        self.lub = None
        self.glb = None


class ChainInfo:
    """Height with one longest chain, and width with one largest antichain."""

    def __init__(self):
        self.height = 0
        self.longest_chain = []          # bottom to top
        self.width = 0
        self.largest_antichain = []


class LatticeReport:
    """The join (lub) and meet (glb) tables and, if it fails, one failing pair."""

    def __init__(self):
        self.is_lattice = False
        self.join_table = []             # join_table[a][b] = index of lub(a,b), or None
        self.meet_table = []             # meet_table[a][b] = index of glb(a,b), or None
        self.fail_a = None
        self.fail_b = None
        self.fail_kind = ""              # "lub" or "glb"
        self.reason = ""
