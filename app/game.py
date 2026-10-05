"""Campaign levels, answer checking, scoring, hints and session state.

Every verdict here comes from the math core (cover_relation, special_elements,
bounds, is_partial_order, compute_closures, lattice_check).
"""

import time

from app.generators import generate_poset, random_int
from app.level_loader import level_input
from core.errors import InputError
from core.hasse import cover_relation
from core.lattice import is_failing_pair, lattice_check
from core.parsers import build_poset, parse_pairs, parse_subset
from core.poset import bounds, is_partial_order, special_elements, strictly_below
from core.relations import compute_closures
from core.steps import label_of, pair_text, set_text, zero_matrix
from core.types import Poset
from core.util import split, trim

HINT_COST_PERCENT = 15
MAX_HINTS = 2
BOSS_TIME_LIMIT_SECONDS = 180


class Feedback:
    """One line of feedback. from_label/to_label are labels to highlight (may be "").

    kind: correct, redundant, unrelated, downward, missing, loop, wrong, extra or info.
    """

    def __init__(self, kind, message, from_label, to_label):
        self.kind = kind
        self.message = message
        self.from_label = from_label
        self.to_label = to_label


class CheckResult:
    """How good an answer is (accuracy 0..1, drives the score) and why."""

    def __init__(self):
        self.accuracy = 0.0
        self.feedback = []
        self.correct_edges = 0          # the edge counters are only used by Hasse checks
        self.wrong_edges = 0
        self.missing_edges = 0
        self.total_covers = 0
        self.precision = 0.0
        self.recall = 0.0


# ======================= Hasse edge checking =======================

def _judge_wrong_edge(p, a, b):
    """Explain why the drawn edge a-b (b drawn above a) is not a covering edge."""
    la, lb = label_of(p, a), label_of(p, b)
    if a == b:
        return Feedback("loop", "Edge " + la + "-" + lb + " is a self-loop. Hasse diagrams never draw (a,a).", la, lb)
    if strictly_below(p, b, a):
        return Feedback("downward", "Edge " + la + "-" + lb + ": direction is upward, smaller below larger. "
                        "Here " + lb + " < " + la + ", so " + la + " must be drawn above " + lb + ".", la, lb)
    if not p.related(a, b):
        return Feedback("unrelated", "(" + la + "," + lb + ") is not in the relation, so " + la + " and " +
                        lb + " must not be joined.", la, lb)
    for c in range(p.size()):
        if strictly_below(p, a, c) and strictly_below(p, c, b):
            return Feedback("redundant", "Edge " + la + "-" + lb + " is redundant. " + la + " < " +
                            label_of(p, c) + " < " + lb + " already forces it by transitivity. "
                            "Hasse diagrams omit it.", la, lb)
    return Feedback("wrong", "Edge " + la + "-" + lb + " is not a covering edge.", la, lb)


def _add_missing_edges(p, covers, drawn, result):
    """Every covering edge the player did not draw: "b covers a: nothing in between"."""
    for (a, b) in covers:
        if (a, b) not in drawn:
            result.missing_edges += 1
            result.feedback.append(Feedback("missing", "Missing edge " + label_of(p, a) + "-" + label_of(p, b) + ": " +
                                            label_of(p, b) + " covers " + label_of(p, a) +
                                            " (nothing sits strictly between them).", label_of(p, a), label_of(p, b)))


def _compute_edge_accuracy(drawn_count, result):
    """precision = correct / drawn, recall = correct / true edges.

    Accuracy combines both: correct / (all true edges + wrong edges drawn).
    """
    if drawn_count == 0:
        result.precision = 1.0 if result.total_covers == 0 else 0.0
    else:
        result.precision = result.correct_edges / drawn_count
    result.recall = 1.0 if result.total_covers == 0 else result.correct_edges / result.total_covers
    denominator = result.total_covers + result.wrong_edges
    result.accuracy = 1.0 if denominator == 0 else result.correct_edges / denominator


def check_hasse_edges(p, edges_text):
    """Judge the player's edges "a>b;c>d" (a>b: b drawn above a) against cover_relation."""
    covers = cover_relation(p)
    drawn = parse_pairs(edges_text, p.labels, None, "edges")
    result = CheckResult()
    result.total_covers = len(covers)
    for (a, b) in drawn:
        if (a, b) in covers:
            result.correct_edges += 1
            result.feedback.append(Feedback("correct", label_of(p, b) + " covers " + label_of(p, a) + ": correct edge.",
                                            label_of(p, a), label_of(p, b)))
        else:
            result.wrong_edges += 1
            result.feedback.append(_judge_wrong_edge(p, a, b))
    _add_missing_edges(p, covers, drawn, result)
    _compute_edge_accuracy(len(drawn), result)
    return result


# ======================= answer helpers =======================

def parse_answer_sections(answer):
    """Split "key:value;key:value" into a dict (keys in lower case)."""
    sections = {}
    for item in split(answer, ";"):
        if item == "":
            continue
        colon = item.find(":")
        if colon < 0:
            raise InputError("Could not read '" + item + "' in the answer; expected name:value.", "answer")
        key = _ascii_lower(trim(item[:colon]))
        sections[key] = trim(item[colon + 1:])
    return sections


def _ascii_lower(text):
    """Lower-case only the letters A-Z (like the original), leaving everything else."""
    result = ""
    for char in text:
        result += chr(ord(char) + 32) if "A" <= char <= "Z" else char
    return result


def _section_value(sections, key):
    return sections.get(key, "")


def _answer_set(p, value):
    """A set of elements from the answer; "none" or "" is the empty set."""
    if value == "none":
        return []
    return parse_subset(value, p.labels, "answer")


def _answer_element(p, value, what):
    """A single element, or None for "none" / ""."""
    chosen = _answer_set(p, value)
    if len(chosen) > 1:
        raise InputError("Pick at most one element for " + what + ".", "answer")
    return chosen[0] if len(chosen) == 1 else None


def _set_similarity(expected, given):
    """Jaccard similarity |A n B| / |A u B| of two index lists (1.0 if both empty)."""
    common = 0
    for x in given:
        if x in expected:
            common += 1
    union_size = len(expected) + len(given) - common
    return 1.0 if union_size == 0 else common / union_size


def _optional_label(p, index):
    return "none" if index is None else label_of(p, index)


# ======================= Spot the Elements =======================

def _judge_extreme_set(p, expected, given, want_minimal, out):
    """Feedback for a minimal (want_minimal) or maximal set answer."""
    name = "minimal" if want_minimal else "maximal"
    for x in given:
        if x in expected:
            out.append(Feedback("correct", label_of(p, x) + " is " + name + ".", label_of(p, x), ""))
            continue
        for y in range(p.size()):
            witness = strictly_below(p, y, x) if want_minimal else strictly_below(p, x, y)
            if witness:
                if want_minimal:
                    rel = label_of(p, y) + " < " + label_of(p, x)
                else:
                    rel = label_of(p, x) + " < " + label_of(p, y)
                out.append(Feedback("wrong", label_of(p, x) + " is not " + name + ": " + rel + ".", label_of(p, x), ""))
                break
    for x in expected:
        if x not in given:
            out.append(Feedback("missing", label_of(p, x) + " is " + name + ": nothing is strictly " +
                                ("below" if want_minimal else "above") + " it.", label_of(p, x), ""))


def _judge_extreme_element(p, expected, given, want_least, candidate_count, out):
    """Feedback for a least (want_least) or greatest single-element answer. Returns 1.0 or 0.0."""
    name = "least" if want_least else "greatest"
    if expected == given:
        if expected is None:
            message = "Correct: there is no " + name + " element."
        else:
            message = label_of(p, expected) + " is the " + name + " element."
        out.append(Feedback("correct", message, _optional_label(p, expected), ""))
        return 1.0
    if expected is None:
        out.append(Feedback("wrong", "There is no " + name + " element: there are " + str(candidate_count) +
                            (" minimal" if want_least else " maximal") + " elements, and a " + name +
                            " element would have to be the only one.", label_of(p, given), ""))
    else:
        out.append(Feedback("missing", label_of(p, expected) + " is the " + name + " element: " +
                            ("it is <= every element." if want_least else "every element is <= it."),
                            label_of(p, expected), ""))
    return 0.0


def check_spot_elements(p, answer):
    """Judge "minimal:1,2;maximal:12;least:1;greatest:none" against special_elements."""
    se = special_elements(p)
    s = parse_answer_sections(answer)
    minimal = _answer_set(p, _section_value(s, "minimal"))
    maximal = _answer_set(p, _section_value(s, "maximal"))
    least = _answer_element(p, _section_value(s, "least"), "the least element")
    greatest = _answer_element(p, _section_value(s, "greatest"), "the greatest element")

    result = CheckResult()
    _judge_extreme_set(p, se.minimal, minimal, True, result.feedback)
    _judge_extreme_set(p, se.maximal, maximal, False, result.feedback)
    total = _set_similarity(se.minimal, minimal) + _set_similarity(se.maximal, maximal)
    total += _judge_extreme_element(p, se.least, least, True, len(se.minimal), result.feedback)
    total += _judge_extreme_element(p, se.greatest, greatest, False, len(se.maximal), result.feedback)
    result.accuracy = total / 4.0
    return result


# ======================= Bounds Challenge =======================

def _judge_bound_set(p, subset, expected, given, want_upper, out):
    """Feedback for the upper (want_upper) or lower bounds the player picked."""
    name = "an upper bound" if want_upper else "a lower bound"
    for x in given:
        if x in expected:
            out.append(Feedback("correct", label_of(p, x) + " is " + name + ".", label_of(p, x), ""))
            continue
        for s in subset:
            holds = p.related(s, x) if want_upper else p.related(x, s)
            if not holds:
                if want_upper:
                    rel = label_of(p, s) + " <= " + label_of(p, x)
                else:
                    rel = label_of(p, x) + " <= " + label_of(p, s)
                out.append(Feedback("wrong", label_of(p, x) + " is not " + name + ": " + rel + " is false.",
                                    label_of(p, x), ""))
                break
    for x in expected:
        if x not in given:
            out.append(Feedback("missing", label_of(p, x) + " is " + name + ": " +
                                ("every element of S is <= it." if want_upper else "it is <= every element of S."),
                                label_of(p, x), ""))


def _judge_best(p, bound_list, expected, given, want_lub, out):
    """Feedback for the lub (want_lub) or glb. Returns 1.0 or 0.0."""
    name = "lub" if want_lub else "glb"
    if expected == given:
        message = "Correct: S has no " + name + "." if expected is None else name + " = " + label_of(p, expected) + "."
        out.append(Feedback("correct", message, _optional_label(p, expected), ""))
        return 1.0
    if expected is None:
        why = ("S has no " + name + ": the " + ("upper" if want_lub else "lower") + " bounds " + set_text(p, bound_list) +
               " have no " + ("least" if want_lub else "greatest") + " element.")
    elif given is not None and given not in bound_list:
        why = (label_of(p, given) + " is not even " + ("an upper" if want_lub else "a lower") +
               " bound, so it cannot be the " + name + ".")
    else:
        why = ("The " + name + " is the " + ("least upper" if want_lub else "greatest lower") + " bound: " +
               label_of(p, expected) + ".")
    out.append(Feedback("wrong", why, _optional_label(p, given), ""))
    return 0.0


def check_bounds_answer(p, subset, answer):
    """Judge "upper:6,12;lower:1;lub:6;glb:none" against bounds()."""
    br = bounds(p, subset)
    s = parse_answer_sections(answer)
    upper = _answer_set(p, _section_value(s, "upper"))
    lower = _answer_set(p, _section_value(s, "lower"))
    lub = _answer_element(p, _section_value(s, "lub"), "the lub")
    glb = _answer_element(p, _section_value(s, "glb"), "the glb")

    result = CheckResult()
    _judge_bound_set(p, subset, br.upper_bounds, upper, True, result.feedback)
    _judge_bound_set(p, subset, br.lower_bounds, lower, False, result.feedback)
    total = _set_similarity(br.upper_bounds, upper) + _set_similarity(br.lower_bounds, lower)
    total += _judge_best(p, br.upper_bounds, br.lub, lub, True, result.feedback)
    total += _judge_best(p, br.lower_bounds, br.glb, glb, False, result.feedback)
    result.accuracy = total / 4.0
    return result


# ======================= Fix the Relation =======================

def _why_required(p, closure, a, c):
    """Explain why a pair of R* is needed: reflexivity, or a chain a -> b -> c."""
    if a == c:
        return pair_text(p, a, a) + " is missing: reflexivity needs (a,a) for every a."
    for b in range(p.size()):
        if b != a and b != c and closure[a][b] == 1 and closure[b][c] == 1:
            return (pair_text(p, a, c) + " is missing: transitivity forces it, because " + pair_text(p, a, b) +
                    " and " + pair_text(p, b, c) + " are in the relation.")
    return pair_text(p, a, c) + " is missing: transitivity forces it."


class _FixCounts:
    """Counts used to score Fix the Relation."""

    def __init__(self):
        self.needed = 0
        self.good_adds = 0
        self.bad_changes = 0


def _judge_fix_pair(original, player, closure, a, b, counts, out):
    """Judge one pair (a,b) by comparing the original R, the player's R' and R*."""
    in_r = original.related(a, b)
    in_new = player.related(a, b)
    in_star = closure[a][b] == 1
    la, lb, pair = label_of(original, a), label_of(original, b), pair_text(original, a, b)
    if in_star and not in_r:
        counts.needed += 1
    if in_r and not in_new:
        counts.bad_changes += 1
        out.append(Feedback("wrong", "You removed " + pair + ". In this level you may only add pairs.", la, lb))
    elif not in_r and in_new and in_star:
        counts.good_adds += 1
        out.append(Feedback("correct", "Adding " + pair + " is needed.", la, lb))
    elif not in_r and in_new:
        counts.bad_changes += 1
        out.append(Feedback("extra", pair + " is not needed: neither reflexivity nor transitivity forces it.", la, lb))
    elif in_star and not in_new:
        out.append(Feedback("missing", _why_required(original, closure, a, b), la, lb))


def check_fix_relation(original, answer):
    """Judge the player's whole corrected relation; only adding pairs is allowed.

    Any partial order containing R contains R*, so the fewest additions are
    exactly R* minus R.
    """
    player = Poset(original.labels, zero_matrix(original.size()))
    for (a, b) in parse_pairs(answer, original.labels, None, "answer"):
        player.R[a][b] = 1
    closure = compute_closures(original).reflexive_transitive     # the unique minimal fix R*

    result = CheckResult()
    counts = _FixCounts()
    for a in range(original.size()):
        for b in range(original.size()):
            _judge_fix_pair(original, player, closure, a, b, counts, result.feedback)
    verdict = is_partial_order(player)
    if verdict.is_poset:
        message = "Your relation is a partial order."
    else:
        message = "Your relation is not a partial order yet. " + verdict.reason
    result.feedback.append(Feedback("info", message, "", ""))
    denominator = counts.needed + counts.bad_changes
    result.accuracy = 1.0 if denominator == 0 else counts.good_adds / denominator
    return result


# ======================= Lattice or Not? =======================

def _judge_failing_pair(p, report, pair, result):
    """The verdict "not a lattice" was right; now check the pair given as justification."""
    if len(pair) != 2:
        result.accuracy = 0.5
        result.feedback.append(Feedback("wrong", "Right verdict. Now justify it: pick the two elements of a failing pair.",
                                        "", ""))
        return
    a, b = label_of(p, pair[0]), label_of(p, pair[1])
    lub = report.join_table[pair[0]][pair[1]]
    glb = report.meet_table[pair[0]][pair[1]]
    bounds_text = "{" + a + "," + b + "} has lub " + _optional_label(p, lub) + " and glb " + _optional_label(p, glb)
    if is_failing_pair(report, pair[0], pair[1]):
        result.accuracy = 1.0
        result.feedback.append(Feedback("correct", "Correct: " + bounds_text + ", so the lattice condition fails.", a, b))
    else:
        result.accuracy = 0.5
        result.feedback.append(Feedback("wrong", "Right verdict, but " + bounds_text + ". Pick a pair that is missing one.",
                                        a, b))


def check_lattice_answer(p, answer):
    """Judge "lattice:yes" or "lattice:no;pair:a,b" against lattice_check."""
    report = lattice_check(p)
    s = parse_answer_sections(answer)
    verdict = _section_value(s, "lattice")
    if verdict != "yes" and verdict != "no":
        raise InputError("Answer 'lattice:yes' or 'lattice:no'.", "answer")
    result = CheckResult()
    if (verdict == "yes") != report.is_lattice:
        if report.is_lattice:
            message = "It IS a lattice: every pair has both a lub and a glb. Check the pairs again."
        else:
            message = "It is NOT a lattice: at least one pair is missing a lub or a glb."
        result.feedback.append(Feedback("wrong", message, "", ""))
        return result
    if report.is_lattice:
        result.accuracy = 1.0
        result.feedback.append(Feedback("correct", "Correct: every pair has a lub and a glb.", "", ""))
        return result
    _judge_failing_pair(p, report, _answer_set(p, _section_value(s, "pair")), result)
    return result


# ======================= Boss =======================

def check_boss_answer(p, answer):
    """Boss = 50% Hasse edges + 25% minimal/maximal + 25% lattice verdict.

    Answer: "edges:a>b,c>d;minimal:..;maximal:..;lattice:yes|no".
    """
    s = parse_answer_sections(answer)
    result = check_hasse_edges(p, _section_value(s, "edges"))
    se = special_elements(p)
    minimal = _answer_set(p, _section_value(s, "minimal"))
    maximal = _answer_set(p, _section_value(s, "maximal"))
    _judge_extreme_set(p, se.minimal, minimal, True, result.feedback)
    _judge_extreme_set(p, se.maximal, maximal, False, result.feedback)
    extremes = (_set_similarity(se.minimal, minimal) + _set_similarity(se.maximal, maximal)) / 2.0

    is_lattice = lattice_check(p).is_lattice
    verdict = _section_value(s, "lattice")
    lattice_right = (verdict == "yes" and is_lattice) or (verdict == "no" and not is_lattice)
    if is_lattice:
        message = "It is a lattice: every pair has a lub and a glb."
    else:
        message = "It is not a lattice: some pair is missing a lub or glb."
    result.feedback.append(Feedback("correct" if lattice_right else "wrong", message, "", ""))
    result.accuracy = 0.5 * result.accuracy + 0.25 * extremes + 0.25 * (1.0 if lattice_right else 0.0)
    return result


# ======================= scoring =======================

def compute_score(points, accuracy, hints_used, attempts):
    """Score = points * accuracy, minus 15% of points per hint and 5% per extra
    attempt (at most 20%), never below 0, rounded to the nearest whole number
    (exact halves round up, e.g. 7.5 -> 8)."""
    extra_attempts = attempts - 1 if attempts > 1 else 0
    if extra_attempts > 4:
        extra_attempts = 4
    # Add the penalties up as a whole-number percentage first, so the
    # subtraction is exact (e.g. 150 points * 5% = 7.5, never 7.4999...).
    penalty_percent = HINT_COST_PERCENT * hints_used + 5 * extra_attempts
    score = points * accuracy - points * penalty_percent / 100
    if score < 0:
        score = 0
    return int(score + 0.5)


def compute_stars(accuracy, hints_used, attempts):
    """Stars only for a fully correct answer: 3 = first try without hints,
    2 = at most two hints/extra attempts in total, otherwise 1. Not solved = 0."""
    if accuracy < 0.999:
        return 0
    slips = hints_used + (attempts - 1 if attempts > 1 else 0)
    if slips == 0:
        return 3
    if slips <= 2:
        return 2
    return 1


# ======================= the session =======================

class LevelProgress:
    """A player's progress on one level."""

    def __init__(self):
        self.attempts = 0
        self.hints_used = 0
        self.best_score = 0
        self.stars = 0
        self.completed = False


class HistoryEntry:
    """One submitted answer, for the score board."""

    def __init__(self, level_id, title, score, stars, accuracy_percent):
        self.level_id = level_id
        self.title = title
        self.score = score
        self.stars = stars
        self.accuracy_percent = accuracy_percent


class LevelView:
    """What the player sees when opening a level."""

    def __init__(self, level, poset, poset_title, unlocked):
        self.level = level
        self.poset = poset
        self.poset_title = poset_title     # e.g. "Divisors of 36" for the boss
        self.unlocked = unlocked


class LevelOutcome:
    """The result of checking one answer."""

    def __init__(self):
        self.check = CheckResult()
        self.passed = False
        self.score = 0
        self.time_bonus = 0                # boss only, measured by the server's clock
        self.elapsed_seconds = 0
        self.stars = 0
        self.attempts = 0
        self.newly_unlocked = []


class HintResult:
    """A hint: number 1 or 2 (0 if no hints left), its text and its cost."""

    def __init__(self, number, text, cost_percent):
        self.number = number
        self.text = text
        self.cost_percent = cost_percent


class GameSession:
    """The one piece of mutable state in the program: a player's session."""

    def __init__(self, levels):
        self.levels = levels
        self.progress_by_id = {}           # level id -> LevelProgress
        self.history = []
        self.unlock_all_levels = False
        self.has_boss = False
        self.boss_poset = Poset()
        self.boss_title = ""
        self.boss_start = 0

    def has_level(self, level_id):
        for level in self.levels:
            if level.id == level_id:
                return True
        return False

    def level(self, level_id):
        for level in self.levels:
            if level.id == level_id:
                return level
        raise InputError("There is no level " + str(level_id) + ".", "level")

    def progress(self, level_id):
        """Progress on a level (a fresh, empty one if the level was never touched)."""
        return self.progress_by_id.get(level_id, LevelProgress())

    def _progress_entry(self, level_id):
        """The stored progress for a level, created on first use."""
        if level_id not in self.progress_by_id:
            self.progress_by_id[level_id] = LevelProgress()
        return self.progress_by_id[level_id]

    def is_unlocked(self, level_id):
        lv = self.level(level_id)
        return (self.unlock_all_levels or lv.unlock_after == 0 or not self.has_level(lv.unlock_after)
                or self.progress(lv.unlock_after).completed)

    def poset_for(self, lv):
        if lv.type == "boss":
            if not self.has_boss:
                raise InputError("Open the Boss level first to generate its poset.", "level")
            return self.boss_poset
        return build_poset(level_input(lv)).poset

    def view(self, level_id):
        """Level details. For the boss this generates a fresh random poset and starts the timer."""
        lv = self.level(level_id)
        unlocked = self.is_unlocked(level_id)
        if lv.type == "boss" and unlocked:
            types = ["divisibility", "subset", "random"]
            generated = generate_poset(types[random_int(0, 2)], random_int(6, 9))
            self.boss_poset = build_poset(generated.input).poset
            self.boss_title = generated.title
            self.boss_start = int(time.time())
            self.has_boss = True
        poset = Poset()
        if lv.type != "boss" or self.has_boss:
            poset = self.poset_for(lv)
        poset_title = self.boss_title if lv.type == "boss" else lv.title
        return LevelView(lv, poset, poset_title, unlocked)

    def _run_checker(self, lv, p, answer):
        if lv.type == "build_hasse":
            return check_hasse_edges(p, answer)
        if lv.type == "spot_elements":
            return check_spot_elements(p, answer)
        if lv.type == "bounds":
            return check_bounds_answer(p, parse_subset(lv.subset, p.labels, "subset"), answer)
        if lv.type == "fix_relation":
            return check_fix_relation(p, answer)
        if lv.type == "lattice":
            return check_lattice_answer(p, answer)
        return check_boss_answer(p, answer)

    def _add_time_bonus(self, lv, out):
        """Boss only: bonus for time left, measured with the server's clock (not the browser's)."""
        out.elapsed_seconds = int(time.time()) - self.boss_start
        left = BOSS_TIME_LIMIT_SECONDS - out.elapsed_seconds
        if out.passed and left > 0:
            out.time_bonus = lv.points // 2 * left // BOSS_TIME_LIMIT_SECONDS
        out.score += out.time_bonus

    def check_level(self, level_id, answer):
        """Check an answer, update progress and unlocks. A malformed answer raises
        InputError before anything is counted."""
        lv = self.level(level_id)
        p = self.poset_for(lv)
        out = LevelOutcome()
        out.check = self._run_checker(lv, p, answer)
        pr = self._progress_entry(level_id)
        pr.attempts += 1
        out.attempts = pr.attempts
        out.passed = out.check.accuracy >= 0.999
        out.score = compute_score(lv.points, out.check.accuracy, pr.hints_used, pr.attempts)
        if lv.type == "boss":
            self._add_time_bonus(lv, out)
        out.stars = compute_stars(out.check.accuracy, pr.hints_used, pr.attempts)
        was_unlocked = [self.is_unlocked(level.id) for level in self.levels]
        pr.best_score = max(pr.best_score, out.score)
        pr.stars = max(pr.stars, out.stars)
        if out.passed:
            pr.completed = True
        for i in range(len(self.levels)):
            if not was_unlocked[i] and self.is_unlocked(self.levels[i].id):
                out.newly_unlocked.append(self.levels[i].id)
        self.history.append(HistoryEntry(level_id, lv.title, out.score, out.stars,
                                         int(out.check.accuracy * 100 + 0.5)))
        return out

    def _hint_text(self, lv, p, number):
        """Hint 1 shows the minimal elements (or, for Fix the Relation, the failing
        axiom); hint 2 reveals one correct piece of the answer with its reason."""
        if lv.type == "fix_relation":
            verdict = is_partial_order(p)
            if number == 1:
                return "The first axiom that fails is '" + verdict.failed_axiom + "'. " + verdict.reason
            return ("The fixed relation must contain the reflexive-transitive closure R*: add every (a,a), then "
                    "keep adding (a,c) whenever (a,b) and (b,c) are present.")
        se = special_elements(p)
        if number == 1:
            return "The minimal elements are " + set_text(p, se.minimal) + ": nothing is strictly below them."
        if lv.type == "build_hasse" or lv.type == "boss":
            return _edge_hint(p)
        if lv.type == "spot_elements":
            return "The maximal elements are " + set_text(p, se.maximal) + "."
        if lv.type == "bounds":
            br = bounds(p, parse_subset(lv.subset, p.labels, "subset"))
            return ("The upper bounds of S are " + set_text(p, br.upper_bounds) +
                    ". The lub is the least of them, if one exists.")
        report = lattice_check(p)
        if report.is_lattice:
            return "Try a few incomparable pairs: each one has both a lub and a glb."
        return "Look closely at pairs involving " + label_of(p, report.fail_a) + "."

    def hint(self, level_id):
        lv = self.level(level_id)
        p = self.poset_for(lv)
        pr = self._progress_entry(level_id)
        if pr.hints_used >= MAX_HINTS:
            return HintResult(0, "No hints left for this level.", 0)
        pr.hints_used += 1
        return HintResult(pr.hints_used, self._hint_text(lv, p, pr.hints_used), HINT_COST_PERCENT)

    def total_score(self):
        total = 0
        for pr in self.progress_by_id.values():
            total += pr.best_score
        return total

    def reset(self):
        self.progress_by_id = {}
        self.history = []
        self.unlock_all_levels = False
        self.has_boss = False

    def unlock_all(self):
        self.unlock_all_levels = True


def _edge_hint(p):
    """Hint 2 for drawing levels: reveal the first covering edge with its reason."""
    covers = cover_relation(p)
    if len(covers) == 0:
        return "There are no covering edges at all: no two distinct elements are related."
    a, b = covers[0]
    return ("Draw " + label_of(p, a) + "-" + label_of(p, b) + ": " + label_of(p, a) + " < " + label_of(p, b) +
            " and no element sits strictly between them, so " + label_of(p, b) + " covers " + label_of(p, a) + ".")
