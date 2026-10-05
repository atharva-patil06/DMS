"""Turns user text into a validated Poset (set A + relation R).

Every API route goes through build_poset(), so validation is written once.
Every error names the offending token and shows an example of the right format.
"""

from core.errors import InputError
from core.steps import add_matrix_step, add_step, label_of, pair_text, zero_matrix
from core.types import MAX_ELEMENTS, Poset
from core.util import is_all_digits, is_valid_label, parse_int, split, split_whitespace, trim


class PosetInput:
    """The raw text fields a user (or a level file) supplies."""

    def __init__(self, elements="", mode="", relation="", matrix="", rule="", auto_reflexive=False):
        self.elements = elements              # "1,2,3,4" or "1 2 3 4" (blank or "{}" = empty set)
        self.mode = mode                      # "pairs", "matrix" or "rule"
        self.relation = relation              # pairs mode: "(1,2), 1<=3, 2>4; ..."
        self.matrix = matrix                  # matrix mode: "0110;0010;..."
        self.rule = rule                      # rule mode: "divisibility", "subset" or "leq"
        self.auto_reflexive = auto_reflexive  # add every missing (a,a), with an explanation


class ParsedPoset:
    """A parsed poset plus notes the UI should show (e.g. "duplicate pair ignored")."""

    def __init__(self):
        self.poset = Poset()
        self.notes = []


# ---------- elements ----------

def _normalise_element_text(text):
    """Turn commas, semicolons and braces into spaces.

    So "{1, 2, 3}", "1,2,3" and "1 2 3" all mean the same set.
    """
    cleaned = ""
    for char in text:
        cleaned += " " if char in ",;{}" else char
    return cleaned


def parse_elements(text):
    """Parse and validate the element list of A.

    Labels must match [A-Za-z0-9_]{1,6}, must not repeat (a set has no
    repeated elements), and there may be at most MAX_ELEMENTS of them.
    """
    labels = split_whitespace(_normalise_element_text(text))
    for i in range(len(labels)):
        if not is_valid_label(labels[i]):
            raise InputError("'" + labels[i] + "' is not a valid element. Use 1 to 6 letters, "
                             "digits or '_', separated by commas, e.g. 1, 2, 3 or a, b, ab.", "elements")
        if index_of_label(labels, labels[i]) != i:
            raise InputError("Element '" + labels[i] + "' is listed twice. A set has no "
                             "repeated elements, so remove the duplicate.", "elements")
    if len(labels) > MAX_ELEMENTS:
        raise InputError("You entered " + str(len(labels)) + " elements; the limit is " +
                         str(MAX_ELEMENTS) + " so the Hasse diagram stays readable.", "elements")
    return labels


def index_of_label(labels, label):
    """Index of a label in the list, or -1 if it is not an element of A."""
    for i in range(len(labels)):
        if labels[i] == label:
            return i
    return -1


# ---------- pairs ----------

def _is_pair_separator(char):
    return char in " \t\r\n,;"


def _is_comparison_char(char):
    return char in "<=>"


def _normalise_pair_text(text):
    """Replace the sign for "less or equal" with "<=" and remove spaces next to < = >.

    So "1 <= 2" and "1 ≤ 2" both become the single token "1<=2".
    """
    with_ascii = text.replace("≤", "<=")
    result = ""
    for i in range(len(with_ascii)):
        char = with_ascii[i]
        if char == " " or char == "\t":
            nxt = i + 1
            while nxt < len(with_ascii) and with_ascii[nxt] in " \t":
                nxt += 1
            next_is_cmp = nxt < len(with_ascii) and _is_comparison_char(with_ascii[nxt])
            prev_is_cmp = result != "" and _is_comparison_char(result[-1])
            if next_is_cmp or prev_is_cmp:
                continue
        result += char
    return result


def _pair_format_help():
    return " Write pairs like (1,2), 1<=2 or 1>2, separated by commas or semicolons."


def _split_comparison(token, field):
    """Split one token such as "1<=2" or "1>2" into its two labels (left, right)."""
    pos = token.find("<=")
    op_length = 2
    if pos < 0:
        pos = token.find(">")
        op_length = 1
    if pos < 0:
        raise InputError("Could not read '" + token + "' in the relation." + _pair_format_help(), field)
    return trim(token[:pos]), trim(token[pos + op_length:])


def _look_up_pair(left, right, labels, field):
    """Convert two labels into an index pair, checking both belong to A."""
    if left == "" or right == "":
        raise InputError("A pair is missing an element near '" + left + "," + right + "'." +
                         _pair_format_help(), field)
    a = index_of_label(labels, left)
    b = index_of_label(labels, right)
    bad = left if a < 0 else right
    if a < 0 or b < 0:
        raise InputError("Pair (" + left + "," + right + ") uses '" + bad + "', which is not in A = {" +
                         ", ".join(labels) + "}. A relation on A may only use elements of A.", field)
    return (a, b)


def _read_paren_pair(text, start, field):
    """Read one "(a,b)" whose '(' is at position start.

    Returns (left, right, index just after ')').
    """
    close = text.find(")", start)
    if close < 0:
        raise InputError("Missing ')' after '" + text[start:] + "'." + _pair_format_help(), field)
    parts = split(text[start + 1:close], ",")
    if len(parts) != 2:
        raise InputError("'" + text[start:close + 1] + "' must contain exactly two elements." +
                         _pair_format_help(), field)
    return parts[0], parts[1], close + 1


def _add_unique_pair(pairs, pair, labels, notes):
    """Add a pair unless it was already seen.

    A relation is a set, so duplicates are ignored (and reported in notes).
    """
    if pair in pairs:
        if notes is not None:
            notes.append("Pair (" + labels[pair[0]] + "," + labels[pair[1]] +
                         ") was listed more than once. A relation is a set, so the copy was ignored.")
        return
    pairs.append(pair)


def parse_pairs(text, labels, notes, field):
    """Parse pair text in any of the forms (a,b)  a<=b  a>b.

    Pairs may be separated by commas, semicolons or spaces. Every element
    must belong to A. Duplicate pairs are dropped and reported in notes
    (which may be None). Returns a list of index pairs (a, b).
    """
    cleaned = _normalise_pair_text(text)
    pairs = []
    i = 0
    while i < len(cleaned):
        if _is_pair_separator(cleaned[i]):
            i += 1
            continue
        if cleaned[i] == "(":
            left, right, i = _read_paren_pair(cleaned, i, field)
        else:
            start = i
            while i < len(cleaned) and not _is_pair_separator(cleaned[i]) and cleaned[i] != "(":
                i += 1
            left, right = _split_comparison(cleaned[start:i], field)
        _add_unique_pair(pairs, _look_up_pair(left, right, labels, field), labels, notes)
    return pairs


# ---------- matrix ----------

def _clean_matrix_row(row):
    """Keep only the meaningful characters of one matrix row ("0 1, 1" -> "011")."""
    cleaned = ""
    for char in row:
        if char not in " ,\t\r":
            cleaned += char
    return cleaned


def parse_matrix(text, n):
    """Parse "0110;0010;..." into an n x n 0/1 matrix (rows by ';' or newline)."""
    rows = []
    for raw_row in split(text.replace("\n", ";"), ";"):
        if _clean_matrix_row(raw_row) != "":
            rows.append(_clean_matrix_row(raw_row))
    if len(rows) != n:
        raise InputError("The matrix has " + str(len(rows)) + " rows but A has " + str(n) +
                         " elements. It must be square: one row and one column per element.", "matrix")
    m = zero_matrix(n)
    for i in range(n):
        if len(rows[i]) != n:
            raise InputError("Row " + str(i + 1) + " has " + str(len(rows[i])) +
                             " entries; it needs exactly " + str(n) + " (e.g. 0110).", "matrix")
        for j in range(n):
            char = rows[i][j]
            if char != "0" and char != "1":
                raise InputError("Matrix entries must be 0 or 1, but row " + str(i + 1) +
                                 " contains '" + char + "'.", "matrix")
            m[i][j] = 1 if char == "1" else 0
    return m


# ---------- rules ----------

def _labels_as_numbers(labels, rule, must_be_positive):
    """Read every label as a number; fail with a rule-specific message."""
    values = []
    for i in range(len(labels)):
        value = parse_int(labels[i]) if is_all_digits(labels[i]) else None
        if value is None or (must_be_positive and value < 1):
            raise InputError("The '" + rule + "' rule needs " + ("positive " if must_be_positive else "") +
                             "whole numbers, but '" + labels[i] + "' is not one. Example: 1, 2, 3, 6.", "elements")
        for j in range(len(values)):
            if values[j] == value:
                raise InputError("'" + labels[j] + "' and '" + labels[i] + "' are the same number. "
                                 "A set has no repeated elements.", "elements")
        values.append(value)
    return values


def _letters_of(label):
    """The set of letters a subset label stands for; "e" is the empty set."""
    letters = set()
    if label == "e":
        return letters
    for char in label:
        is_letter = ("a" <= char <= "z") or ("A" <= char <= "Z")
        if not is_letter or char in letters:
            raise InputError("For subset inclusion each element must be a set of distinct letters "
                             "(e.g. a, ab, abc; 'e' is the empty set), but '" + label + "' is not.", "elements")
        letters.add(char)
    return letters


def _subset_matrix(labels):
    """Subset inclusion: A R B exactly when every letter of A is also in B."""
    n = len(labels)
    sets = []
    for i in range(n):
        sets.append(_letters_of(labels[i]))
        for j in range(i):
            if sets[j] == sets[i]:
                raise InputError("'" + labels[j] + "' and '" + labels[i] + "' are the same set. "
                                 "A set has no repeated elements.", "elements")
    m = zero_matrix(n)
    for i in range(n):
        for j in range(n):
            m[i][j] = 1 if sets[i].issubset(sets[j]) else 0
    return m


def rule_matrix(labels, rule):
    """Build the relation matrix for a named rule on the given labels.

    divisibility: a R b <=> a divides b        (labels must be positive integers)
    leq:          a R b <=> a <= b             (labels must be integers)
    subset:       a R b <=> a is a subset of b (labels are sets of letters, "e" = empty set)
    """
    n = len(labels)
    if rule == "subset":
        return _subset_matrix(labels)
    if rule != "divisibility" and rule != "leq":
        raise InputError("Unknown rule '" + rule + "'. Choose divisibility, subset or leq.", "rule")
    values = _labels_as_numbers(labels, rule, rule == "divisibility")
    m = zero_matrix(n)
    for i in range(n):
        for j in range(n):
            if rule == "divisibility":
                m[i][j] = 1 if values[j] % values[i] == 0 else 0     # a | b
            else:
                m[i][j] = 1 if values[i] <= values[j] else 0         # a <= b
    return m


# ---------- subsets ----------

def parse_subset(text, labels, field):
    """Parse a subset S of A, e.g. "2,3". Repeated labels are counted once."""
    subset = []
    for name in split_whitespace(_normalise_element_text(text)):
        index = index_of_label(labels, name)
        if index < 0:
            raise InputError("'" + name + "' is not in A = {" + ", ".join(labels) +
                             "}, so it cannot be in the subset S.", field)
        if index not in subset:
            subset.append(index)
    return subset


# ---------- full pipeline ----------

def _relation_from_input(poset_input, labels, notes):
    """Fill R from the chosen input mode."""
    n = len(labels)
    if poset_input.mode == "pairs":
        m = zero_matrix(n)
        for (a, b) in parse_pairs(poset_input.relation, labels, notes, "relation"):
            m[a][b] = 1
        return m
    if poset_input.mode == "matrix":
        return parse_matrix(poset_input.matrix, n)
    if poset_input.mode == "rule":
        return rule_matrix(labels, poset_input.rule)
    raise InputError("Unknown input mode '" + poset_input.mode + "'. Use pairs, matrix or rule.", "mode")


def _add_reflexive_pairs(poset, notes, steps):
    """The "auto-add reflexive pairs" option.

    We add each missing (a,a) and say so explicitly, instead of silently
    changing the user's relation.
    """
    added = []
    for i in range(poset.size()):
        if not poset.related(i, i):
            poset.R[i][i] = 1
            added.append(i)
    if len(added) == 0:
        return
    pair_list = ", ".join(pair_text(poset, i, i) for i in added)
    message = ("Auto-added reflexive pairs " + pair_list +
               " because 'auto-add reflexive pairs' is ticked (a partial order needs (a,a) for every a).")
    notes.append(message)
    add_step(steps, "Auto-add reflexive pairs", message, "INFO")


def build_poset(poset_input, steps=None):
    """Full pipeline used by every route: elements + chosen mode -> ParsedPoset."""
    parsed = ParsedPoset()
    parsed.poset.labels = parse_elements(poset_input.elements)
    n = parsed.poset.size()
    parsed.poset.R = _relation_from_input(poset_input, parsed.poset.labels, parsed.notes)
    add_step(steps, "Read the set A", "A = {" + ", ".join(parsed.poset.labels) + "}, |A| = " + str(n), "INFO")
    if n == 0:
        parsed.notes.append("A is the empty set. Every property holds vacuously (there is nothing to check).")
    if poset_input.auto_reflexive:
        _add_reflexive_pairs(parsed.poset, parsed.notes, steps)
    add_matrix_step(steps, "Relation matrix M(R)",
                    "Row i, column j is 1 exactly when (ai, aj) is in R.", parsed.poset.R)
    return parsed


# ---------- generators of element lists ----------

def divisor_labels(n):
    """Labels of all positive divisors of n, e.g. 12 -> 1 2 3 4 6 12."""
    if n < 1:
        raise InputError("n must be a positive whole number to list its divisors.", "n")
    labels = []
    for d in range(1, n + 1):
        if n % d == 0:
            labels.append(str(d))
        if len(labels) > MAX_ELEMENTS:
            raise InputError(str(n) + " has more than " + str(MAX_ELEMENTS) +
                             " divisors; pick a smaller n (e.g. 12, 24, 30, 36, 48, 60).", "n")
    return labels


def power_set_labels(letters):
    """Labels of all subsets of the given letters, e.g. "ab" -> e a b ab."""
    k = len(letters)
    if k < 1 or k > 3 or letters == "e":
        raise InputError("A power set of " + str(k) + " letters has 2^" + str(k) +
                         " elements; use 1 to 3 letters (limit " + str(MAX_ELEMENTS) + ").", "letters")
    _letters_of(letters)   # raises if the letters repeat or are not letters
    labels = []
    for mask in range(1 << k):
        label = ""
        for bit in range(k):
            if mask & (1 << bit):
                label += letters[bit]
        labels.append(label if label != "" else "e")
    return labels


def pairs_to_text(poset, skip_reflexive):
    """Write a relation in the wire format "a>b;c>d" (a>b means (a,b) in R).

    If skip_reflexive is True the pairs (a,a) are left out.
    """
    items = []
    for i in range(poset.size()):
        for j in range(poset.size()):
            if poset.related(i, j) and not (skip_reflexive and i == j):
                items.append(label_of(poset, i) + ">" + label_of(poset, j))
    return ";".join(items)
