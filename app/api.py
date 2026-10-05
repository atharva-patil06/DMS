"""The routes: request fields -> core/game calls -> JSON.

No mathematics happens here: every answer comes from core/ or game.py.
Routes (all JSON, {"ok": true, ...} or {"ok": false, "error": ..., "field": ...}):
  POST /api/analyze              full analysis of a set + relation
  POST /api/bounds               bounds, lub, glb of a subset
  POST /api/check-hasse          judge drawn Hasse edges
  GET  /api/levels               level list with progress
  GET  /api/levels/<id>          one level's details
  POST /api/levels/<id>/check    check an answer
  POST /api/levels/<id>/hint     get a hint (costs points)
  GET  /api/generate?type=..     random poset, or divisors / power set lists
  GET  /api/score                total score and history
  POST /api/reset, /api/unlock-all
"""

from flask import jsonify, request

from app import server
from app.game import BOSS_TIME_LIMIT_SECONDS, HINT_COST_PERCENT, check_hasse_edges, compute_score
from app.generators import GeneratedPoset, generate_poset
from app.server import app, body_fields, error_reply, query_fields
from core.errors import InputError
from core.hasse import cover_relation, hasse_levels
from core.lattice import lattice_check
from core.parsers import PosetInput, build_poset, divisor_labels, pairs_to_text, parse_subset, power_set_labels
from core.poset import chains_and_antichains, is_partial_order, special_elements
from core.poset import bounds as compute_bounds
from core.relations import compute_closures, equivalence_classes
from core.steps import add_step, set_text
from core.util import parse_int, split


# ======================= small conversion helpers =======================

def _labels(p, indices):
    """Index list -> label list, e.g. [0, 2] -> ["1", "3"]."""
    return [p.labels[i] for i in indices]


def _optional_label(p, index):
    """A label, or None (JSON null) when the element does not exist."""
    return None if index is None else p.labels[index]


def _pairs_json(p, pairs):
    """[(0, 1)] -> [["1", "2"]]."""
    return [[p.labels[a], p.labels[b]] for (a, b) in pairs]


def _label_table(p, table):
    """A join/meet table: each cell is a label, or None when the bound is missing."""
    return [[_optional_label(p, cell) for cell in row] for row in table]


def _steps_json(steps):
    """The Show Working steps; "matrix" only appears when the step has one."""
    result = []
    for step in steps:
        item = {"title": step.title, "detail": step.detail, "result": step.result}
        if len(step.matrix) > 0:
            item["matrix"] = step.matrix
        result.append(item)
    return result


def _feedback_json(feedback):
    return [{"kind": f.kind, "message": f.message, "from": f.from_label, "to": f.to_label} for f in feedback]


def _property_json(check):
    return {"holds": check.holds, "counterexample": check.counterexample}


def _percent(fraction):
    """0.333 -> 33 (rounded half up, like the original)."""
    return int(fraction * 100 + 0.5)


def _ok(reply):
    """Return a reply dict as JSON with status 200."""
    return jsonify(reply)


# ======================= request fields =======================

def _require_field(fields, name):
    if name not in fields:
        raise InputError("The request is missing the field '" + name + "'.", name)
    return fields[name]


def _int_field(fields, name, fallback):
    text = fields.get(name, "")
    if text == "":
        return fallback
    value = parse_int(text)
    if value is None:
        raise InputError("'" + name + "' must be a whole number, got '" + text + "'.", name)
    return value


def poset_input_from_fields(fields):
    """Read the poset fields shared by several routes into a core PosetInput."""
    poset_input = PosetInput()
    poset_input.elements = _require_field(fields, "elements")
    poset_input.mode = fields.get("mode", "pairs")
    if poset_input.mode == "pairs":
        poset_input.relation = _require_field(fields, "relation")
    if poset_input.mode == "matrix":
        poset_input.matrix = _require_field(fields, "matrix")
    if poset_input.mode == "rule":
        poset_input.rule = _require_field(fields, "rule")
    poset_input.auto_reflexive = fields.get("auto_reflexive", "0") == "1"
    return poset_input


# ======================= /api/analyze =======================

def _add_shape_notes(p, verdict, notes):
    """Friendly notes for the special shapes listed in the spec's edge cases."""
    pair_count = sum(sum(row) for row in p.R)
    if p.size() > 0 and pair_count == 0:
        notes.append("R is the empty relation: no pairs at all, so it is not reflexive.")
    if p.size() == 1 and verdict.is_poset:
        notes.append("A has a single element: the only partial order is {(a,a)}, which is trivially a lattice.")
    if verdict.is_poset and verdict.is_total_order and p.size() > 1:
        notes.append("Every two elements are comparable: this is a total order (a chain), so the Hasse "
                     "diagram is a straight line.")
    if verdict.is_poset and verdict.is_antichain and p.size() > 1:
        notes.append("Only reflexive pairs: this poset is an antichain, so the Hasse diagram has no edges.")


def _properties_section(reply, p, verdict):
    props = verdict.properties
    reply["properties"] = {
        "reflexive": _property_json(props.reflexive),
        "symmetric": _property_json(props.symmetric),
        "antisymmetric": _property_json(props.antisymmetric),
        "transitive": _property_json(props.transitive),
    }
    reply["isEquivalence"] = props.is_equivalence
    if props.is_equivalence:
        reply["equivalenceClasses"] = [_labels(p, cls) for cls in equivalence_classes(p)]
    reply["isPoset"] = verdict.is_poset
    reply["failedAxiom"] = verdict.failed_axiom
    reply["reason"] = verdict.reason
    reply["hasCycle"] = verdict.has_cycle


def _lattice_section(reply, p, steps):
    """The lattice verdict and the full join (lub) / meet (glb) tables."""
    add_step(steps, "Lattice check: lub and glb of every pair", "", "HEAD")
    report = lattice_check(p, steps)
    reply["lattice"] = {
        "isLattice": report.is_lattice,
        "reason": report.reason,
        "failPair": None if report.fail_a is None else _labels(p, [report.fail_a, report.fail_b]),
        "join": _label_table(p, report.join_table),
        "meet": _label_table(p, report.meet_table),
    }


def _poset_section(reply, p, verdict, steps):
    """Everything that only makes sense for a partial order."""
    reply["isTotalOrder"] = verdict.is_total_order
    reply["isAntichain"] = verdict.is_antichain
    add_step(steps, "Hasse diagram: covering relation", "", "HEAD")
    reply["covers"] = _pairs_json(p, cover_relation(p, steps))
    reply["levels"] = hasse_levels(p)
    add_step(steps, "Special elements", "", "HEAD")
    se = special_elements(p, steps)
    reply["minimal"] = _labels(p, se.minimal)
    reply["maximal"] = _labels(p, se.maximal)
    reply["least"] = _optional_label(p, se.least)
    reply["greatest"] = _optional_label(p, se.greatest)
    chains = chains_and_antichains(p)
    reply["height"] = chains.height
    reply["longestChain"] = _labels(p, chains.longest_chain)
    reply["width"] = chains.width
    reply["largestAntichain"] = _labels(p, chains.largest_antichain)
    _lattice_section(reply, p, steps)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    steps = []
    add_step(steps, "Input", "", "HEAD")
    parsed = build_poset(poset_input_from_fields(body_fields()), steps)
    p = parsed.poset
    add_step(steps, "Relation properties", "", "HEAD")
    verdict = is_partial_order(p, steps)
    add_step(steps, "Closures (Warshall's algorithm)", "", "HEAD")
    closures = compute_closures(p, steps)
    _add_shape_notes(p, verdict, parsed.notes)

    reply = {"ok": True, "elements": p.labels, "matrix": p.R, "notes": parsed.notes}
    _properties_section(reply, p, verdict)
    reply["closures"] = {"reflexive": closures.reflexive, "symmetric": closures.symmetric,
                         "transitive": closures.transitive}
    if verdict.is_poset:
        _poset_section(reply, p, verdict, steps)
    reply["steps"] = _steps_json(steps)
    return _ok(reply)


# ======================= /api/bounds and /api/check-hasse =======================

@app.route("/api/bounds", methods=["POST"])
def bounds_route():
    fields = body_fields()
    p = build_poset(poset_input_from_fields(fields)).poset
    subset = parse_subset(_require_field(fields, "subset"), p.labels, "subset")
    steps = []
    add_step(steps, "Bounds of S = " + set_text(p, subset), "", "HEAD")
    br = compute_bounds(p, subset, steps)
    return _ok({"ok": True, "subset": _labels(p, subset), "upperBounds": _labels(p, br.upper_bounds),
                "lowerBounds": _labels(p, br.lower_bounds), "lub": _optional_label(p, br.lub),
                "glb": _optional_label(p, br.glb), "steps": _steps_json(steps)})


def _check_result_json(reply, result):
    reply["accuracy"] = _percent(result.accuracy)
    reply["correctEdges"] = result.correct_edges
    reply["wrongEdges"] = result.wrong_edges
    reply["missingEdges"] = result.missing_edges
    reply["totalCovers"] = result.total_covers
    reply["precision"] = _percent(result.precision)
    reply["recall"] = _percent(result.recall)
    reply["feedback"] = _feedback_json(result.feedback)


@app.route("/api/check-hasse", methods=["POST"])
def check_hasse():
    fields = body_fields()
    p = build_poset(poset_input_from_fields(fields)).poset
    result = check_hasse_edges(p, _require_field(fields, "edges"))
    reply = {"ok": True}
    _check_result_json(reply, result)
    reply["score"] = compute_score(100, result.accuracy, 0, 1)
    reply["passed"] = result.accuracy >= 0.999
    return _ok(reply)


# ======================= levels =======================

def _progress_json(reply, progress):
    reply["completed"] = progress.completed
    reply["stars"] = progress.stars
    reply["bestScore"] = progress.best_score
    reply["attempts"] = progress.attempts
    reply["hintsUsed"] = progress.hints_used


def _max_score():
    return sum(level.points for level in server.session.levels)


@app.route("/api/levels", methods=["GET"])
def level_list():
    session = server.session
    levels = []
    for level in session.levels:
        item = {"id": level.id, "title": level.title, "type": level.type, "points": level.points,
                "unlocked": session.is_unlocked(level.id)}
        _progress_json(item, session.progress(level.id))
        levels.append(item)
    return _ok({"ok": True, "totalScore": session.total_score(), "maxScore": _max_score(), "levels": levels})


def _visible_pairs(p):
    """Non-reflexive pairs of R: what we show the player as "the relation"."""
    pairs = []
    for i in range(p.size()):
        for j in range(p.size()):
            if i != j and p.related(i, j):
                pairs.append((i, j))
    return pairs


def _level_details(level_id):
    v = server.session.view(level_id)
    p = v.poset
    show_diagram = v.level.type in ("spot_elements", "bounds", "lattice")
    reply = {"ok": True, "id": v.level.id, "type": v.level.type, "title": v.level.title,
             "description": v.level.description, "tip": v.level.hint, "points": v.level.points,
             "posetTitle": v.poset_title, "elements": p.labels, "matrix": p.R}
    if show_diagram:
        reply["covers"] = _pairs_json(p, cover_relation(p))
        reply["levels"] = hasse_levels(p)
    reply["pairs"] = _pairs_json(p, _visible_pairs(p))
    reply["relationText"] = pairs_to_text(p, v.level.type != "fix_relation")
    if v.level.type == "bounds":
        reply["subset"] = _labels(p, parse_subset(v.level.subset, p.labels, "subset"))
    if v.level.type == "boss":
        reply["timeLimit"] = BOSS_TIME_LIMIT_SECONDS
    reply["costPercent"] = HINT_COST_PERCENT
    _progress_json(reply, server.session.progress(level_id))
    return _ok(reply)


def _level_check(level_id, fields):
    session = server.session
    out = session.check_level(level_id, _require_field(fields, "answer"))
    reply = {"ok": True, "passed": out.passed, "score": out.score, "stars": out.stars, "attempts": out.attempts,
             "timeBonus": out.time_bonus, "elapsedSeconds": out.elapsed_seconds}
    _check_result_json(reply, out.check)
    reply["newlyUnlocked"] = out.newly_unlocked
    reply["bestScore"] = session.progress(level_id).best_score
    reply["totalScore"] = session.total_score()
    return _ok(reply)


def _level_hint(level_id):
    hint = server.session.hint(level_id)
    return _ok({"ok": True, "number": hint.number, "text": hint.text, "costPercent": hint.cost_percent,
                "hintsUsed": server.session.progress(level_id).hints_used})


@app.route("/api/levels/<path:rest>", methods=["GET", "POST"])
def level_route(rest):
    """/api/levels/<id>[/check|/hint]: checks the id, the lock, then the action."""
    session = server.session
    parts = split(rest, "/")
    level_id = parse_int(parts[0])
    if level_id is None or not session.has_level(level_id):
        return error_reply(404, "There is no level '" + parts[0] + "'.", "level")
    if not session.is_unlocked(level_id):
        return error_reply(403, "This level is locked. Complete level " +
                           str(session.level(level_id).unlock_after) + " first.", "level")
    action = parts[1] if len(parts) > 1 else ""
    if action == "" and request.method == "GET":
        return _level_details(level_id)
    if action == "check" and request.method == "POST":
        return _level_check(level_id, body_fields())
    if action == "hint" and request.method == "POST":
        return _level_hint(level_id)
    return error_reply(404, "Unknown level action.", "path")


# ======================= generate, score, reset =======================

def _element_list_generator(gen_type, fields):
    """'divisors' and 'powerset': fixed element lists computed by the core."""
    if gen_type == "divisors":
        n = _int_field(fields, "n", 12)
        return GeneratedPoset("Divisors of " + str(n),
                              PosetInput(elements=", ".join(divisor_labels(n)), mode="rule", rule="divisibility"))
    letters = fields.get("letters", "abc")
    return GeneratedPoset("Power set of {" + letters + "}",
                          PosetInput(elements=", ".join(power_set_labels(letters)), mode="rule", rule="subset"))


@app.route("/api/generate", methods=["GET"])
def generate():
    fields = query_fields()
    gen_type = _require_field(fields, "type")
    if gen_type == "divisors" or gen_type == "powerset":
        generated = _element_list_generator(gen_type, fields)
        generated.type = gen_type
    else:
        generated = generate_poset(gen_type, _int_field(fields, "size", 8))
    g = generated.input
    return _ok({"ok": True, "type": generated.type, "title": generated.title, "elements": g.elements,
                "mode": g.mode, "rule": g.rule, "relation": g.relation, "autoReflexive": g.auto_reflexive})


@app.route("/api/score", methods=["GET"])
def score():
    session = server.session
    history = [{"levelId": h.level_id, "title": h.title, "score": h.score, "stars": h.stars,
                "accuracy": h.accuracy_percent} for h in session.history]
    return _ok({"ok": True, "totalScore": session.total_score(), "maxScore": _max_score(), "history": history})


@app.route("/api/reset", methods=["POST"])
def reset():
    server.session.reset()
    return _ok({"ok": True})


@app.route("/api/unlock-all", methods=["POST"])
def unlock_all():
    server.session.unlock_all()
    return _ok({"ok": True})
