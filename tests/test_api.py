"""Every route in docs/API_CONTRACT.md, through Flask's test client (no network)."""

import pytest

from conftest import LEVELS_DIR
from test_game import two_levels
from app import server
from app.game import GameSession
from app.level_loader import load_levels
from app.server import RequestError, app, parse_form, percent_decode

FORM = {"Content-Type": "application/x-www-form-urlencoded"}


@pytest.fixture
def client():
    """A test client with a fresh two-level session for every test."""
    server.session = GameSession(two_levels())
    return app.test_client()


@pytest.fixture
def campaign_client():
    """A test client with the real campaign levels, all unlocked."""
    server.session = GameSession(load_levels(LEVELS_DIR))
    server.session.unlock_all()
    return app.test_client()


def post(client, path, body):
    return client.post(path, data=body, headers=FORM)


# ---------- ported from the C++ tests (form decoding, JSON, API) ----------

def test_http_request_parsing():
    assert percent_decode("a%3Eb+c") == "a>b c"
    fields = parse_form("elements=1%2C2&relation=1%3E2&empty=")
    assert fields["elements"] == "1,2"
    assert fields["relation"] == "1>2"
    assert fields["empty"] == ""


def test_http_request_rejects_malformed_input(client):
    with pytest.raises(RequestError) as caught:
        percent_decode("bad%G1")
    assert caught.value.status == 400
    assert client.delete("/api/levels").status_code == 405
    big = client.post("/api/analyze", data="x" * (1024 * 1024 + 10), headers=FORM)
    assert big.status_code == 413
    assert big.get_json() == {"ok": False, "error": "Request body is too large (limit 1 MB).", "field": "request"}


def test_json_reply_keeps_text_and_key_order(client):
    r = post(client, "/api/analyze", 'elements=a&mode=pairs&relation=')
    body = r.get_data(as_text=True)
    assert body.startswith('{"ok":true,"elements":["a"],"matrix":[[0]],"notes":')
    assert r.get_json()["steps"][0] == {"title": "Input", "detail": "", "result": "HEAD"}


def test_api_analyze_returns_full_json(client):
    r = post(client, "/api/analyze", "elements=1,2,3,6&mode=rule&rule=divisibility")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["isPoset"] is True
    assert data["covers"] == [["1", "2"], ["1", "3"], ["2", "6"], ["3", "6"]]
    assert data["lattice"]["isLattice"] is True
    assert any(step["title"].startswith("Warshall step") for step in data["steps"])


def test_api_errors_are_friendly_json(client):
    bad = post(client, "/api/analyze", "elements=1,2&mode=pairs&relation=1>9")
    assert bad.status_code == 400
    assert bad.get_json()["ok"] is False
    assert bad.get_json()["field"] == "relation"
    missing = post(client, "/api/analyze", "mode=pairs")
    assert missing.get_json()["field"] == "elements"
    encoding = post(client, "/api/analyze", "elements=%ZZ")
    assert encoding.status_code == 400
    assert client.get("/api/nothing").status_code == 404
    assert client.get("/api/levels/2").status_code == 403


def test_api_bounds_and_check_hasse_routes(client):
    b = post(client, "/api/bounds", "elements=1,2,3,6&mode=rule&rule=divisibility&subset=2,3").get_json()
    assert b["lub"] == "6"
    assert b["glb"] == "1"
    c = post(client, "/api/check-hasse",
             "elements=1,2,4&mode=rule&rule=divisibility&edges=1>2;2>4;1>4").get_json()
    assert any(f["kind"] == "redundant" for f in c["feedback"])
    assert c["passed"] is False


# ---------- every route in the contract ----------

def test_api_analyze_keys_for_a_poset(client):
    data = post(client, "/api/analyze", "elements=1,2,4&mode=rule&rule=divisibility").get_json()
    assert list(data.keys()) == ["ok", "elements", "matrix", "notes", "properties", "isEquivalence", "isPoset",
                                 "failedAxiom", "reason", "hasCycle", "closures", "isTotalOrder", "isAntichain",
                                 "covers", "levels", "minimal", "maximal", "least", "greatest", "height",
                                 "longestChain", "width", "largestAntichain", "lattice", "steps"]
    assert data["notes"] == ["Every two elements are comparable: this is a total order (a chain), so the Hasse "
                             "diagram is a straight line."]
    assert data["levels"] == [0, 1, 2]
    assert data["least"] == "1"
    assert data["lattice"]["failPair"] is None
    heads = [s["title"] for s in data["steps"] if s["result"] == "HEAD"]
    assert heads == ["Input", "Relation properties", "Closures (Warshall's algorithm)",
                     "Hasse diagram: covering relation", "Special elements",
                     "Lattice check: lub and glb of every pair"]


def test_api_analyze_not_a_poset(client):
    data = post(client, "/api/analyze", "elements=1,2&mode=pairs&relation=1>2;2>1&auto_reflexive=1").get_json()
    assert data["isPoset"] is False
    assert data["failedAxiom"] == "antisymmetric"
    assert data["equivalenceClasses"] == [["1", "2"]]
    assert data["hasCycle"] is True
    assert "covers" not in data
    assert list(data.keys())[-1] == "steps"
    assert data["notes"][0].startswith("Auto-added reflexive pairs (1,1), (2,2)")


def test_api_analyze_matrix_mode_and_not_a_lattice(client):
    data = post(client, "/api/analyze", "elements=a,b,c,d&mode=pairs&relation=a>c;b>c;b>d&auto_reflexive=1").get_json()
    assert data["lattice"]["isLattice"] is False
    assert data["lattice"]["failPair"] == ["a", "b"]
    assert data["lattice"]["join"][0][1] == "c"
    assert data["lattice"]["meet"][0][1] is None
    m = post(client, "/api/analyze", "elements=a,b,c&mode=matrix&matrix=110;010;111").get_json()
    assert m["covers"] == [["a", "b"], ["c", "a"]]


def test_api_bounds_steps_and_errors(client):
    data = post(client, "/api/bounds", "elements=1,2,3,6&mode=rule&rule=divisibility&subset=2,3").get_json()
    assert data["steps"][0] == {"title": "Bounds of S = {2, 3}", "detail": "", "result": "HEAD"}
    assert data["steps"][1]["detail"] == "Upper bound? 2<=1 no, 3<=1 no.  Lower bound? 1<=2 yes, 1<=3 yes."
    assert post(client, "/api/bounds", "elements=1,2,3&mode=rule&rule=divisibility&subset=9").get_json()["field"] == "subset"
    not_poset = post(client, "/api/bounds", "elements=1,2&mode=pairs&relation=1>2;2>1&subset=1").get_json()
    assert not_poset["field"] == "relation"
    assert not_poset["error"].startswith("Cannot compute bounds because R is not a partial order.")


def test_api_check_hasse_matches_recorded_reply(client):
    data = post(client, "/api/check-hasse", "elements=1,2,4&mode=rule&rule=divisibility&edges=1>2;1>4").get_json()
    assert data == {"ok": True, "accuracy": 33, "correctEdges": 1, "wrongEdges": 1, "missingEdges": 1,
                    "totalCovers": 2, "precision": 50, "recall": 50,
                    "feedback": [{"kind": "correct", "message": "2 covers 1: correct edge.", "from": "1", "to": "2"},
                                 {"kind": "redundant", "message": "Edge 1-4 is redundant. 1 < 2 < 4 already forces "
                                  "it by transitivity. Hasse diagrams omit it.", "from": "1", "to": "4"},
                                 {"kind": "missing", "message": "Missing edge 2-4: 4 covers 2 (nothing sits "
                                  "strictly between them).", "from": "2", "to": "4"}],
                    "score": 33, "passed": False}


def test_api_levels_list(campaign_client):
    data = campaign_client.get("/api/levels").get_json()
    assert data["maxScore"] == 1850
    assert data["levels"][0] == {"id": 1, "title": "Divisors of 12", "type": "build_hasse", "points": 100,
                                 "unlocked": True, "completed": False, "stars": 0, "bestScore": 0,
                                 "attempts": 0, "hintsUsed": 0}


def test_api_level_details_by_type(campaign_client):
    bounds_level = campaign_client.get("/api/levels/6").get_json()
    assert list(bounds_level.keys()) == ["ok", "id", "type", "title", "description", "tip", "points", "posetTitle",
                                         "elements", "matrix", "covers", "levels", "pairs", "relationText", "subset",
                                         "costPercent", "completed", "stars", "bestScore", "attempts", "hintsUsed"]
    assert bounds_level["subset"] == ["4", "6"]
    build = campaign_client.get("/api/levels/1").get_json()
    assert "covers" not in build
    fix = campaign_client.get("/api/levels/8").get_json()
    assert fix["relationText"] == "1>2;2>3;3>4"
    boss = campaign_client.get("/api/levels/13").get_json()
    assert boss["timeLimit"] == 180
    assert 6 <= len(boss["elements"]) <= 9


def test_api_level_check_and_hint(campaign_client):
    check = post(campaign_client, "/api/levels/9/check",
                 "answer=a>a;b>b;c>c;d>d;a>b;b>d;a>c;c>d;a>d").get_json()
    assert check == {"ok": True, "passed": True, "score": 100, "stars": 3, "attempts": 1, "timeBonus": 0,
                     "elapsedSeconds": 0, "accuracy": 100, "correctEdges": 0, "wrongEdges": 0, "missingEdges": 0,
                     "totalCovers": 0, "precision": 0, "recall": 0,
                     "feedback": [{"kind": "correct", "message": "Adding (a,d) is needed.", "from": "a", "to": "d"},
                                  {"kind": "info", "message": "Your relation is a partial order.", "from": "", "to": ""}],
                     "newlyUnlocked": [], "bestScore": 100, "totalScore": 100}
    hint = post(campaign_client, "/api/levels/4/hint", "").get_json()
    assert hint == {"ok": True, "number": 1, "text": "The minimal elements are {2, 3}: nothing is strictly below them.",
                    "costPercent": 15, "hintsUsed": 1}


def test_api_level_errors(client):
    assert client.get("/api/levels/99").get_json() == {"ok": False, "error": "There is no level '99'.", "field": "level"}
    assert client.get("/api/levels/abc").status_code == 404
    locked = post(client, "/api/levels/2/check", "answer=x")
    assert locked.status_code == 403
    assert locked.get_json()["error"] == "This level is locked. Complete level 1 first."
    action = post(client, "/api/levels/1/xyz", "")
    assert action.status_code == 404
    assert action.get_json() == {"ok": False, "error": "Unknown level action.", "field": "path"}
    assert client.get("/api/levels/1/check").status_code == 404
    bad_answer = post(client, "/api/levels/1/check", "answer=1>9")
    assert bad_answer.status_code == 400
    assert bad_answer.get_json()["field"] == "edges"
    assert server.session.progress(1).attempts == 0          # a malformed answer is not counted
    assert post(client, "/api/levels/1/check", "").get_json()["field"] == "answer"


def test_api_boss_needs_to_be_opened_first(campaign_client):
    r = post(campaign_client, "/api/levels/13/check", "answer=edges:;minimal:;maximal:;lattice:yes")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Open the Boss level first to generate its poset."


def test_api_generate_all_types(client):
    leq = client.get("/api/generate?type=leq&size=3").get_json()
    assert list(leq.keys()) == ["ok", "type", "title", "elements", "mode", "rule", "relation", "autoReflexive"]
    assert leq["title"] == "Numbers under <="
    assert len(leq["elements"].split(" ")) == 3
    divisors = client.get("/api/generate?type=divisors&n=12").get_json()
    assert divisors["elements"] == "1, 2, 3, 4, 6, 12"
    assert client.get("/api/generate?type=powerset&letters=ab").get_json()["elements"] == "e, a, b, ab"
    random_poset = client.get("/api/generate?type=random&size=5").get_json()
    assert random_poset["mode"] == "pairs" and random_poset["autoReflexive"] is True
    assert client.get("/api/generate?type=random&size=abc").get_json() == {
        "ok": False, "error": "'size' must be a whole number, got 'abc'.", "field": "size"}
    assert client.get("/api/generate?type=divisors&n=720").get_json()["field"] == "n"
    assert client.get("/api/generate?type=magic").get_json()["field"] == "type"
    assert client.get("/api/generate").get_json()["field"] == "type"


def test_api_score_reset_and_unlock_all(client):
    post(client, "/api/levels/1/check", "answer=1>2;2>4")
    score = client.get("/api/score").get_json()
    assert score == {"ok": True, "totalScore": 100, "maxScore": 150,
                     "history": [{"levelId": 1, "title": "A", "score": 100, "stars": 3, "accuracy": 100}]}
    assert post(client, "/api/reset", "").get_json() == {"ok": True}
    assert client.get("/api/score").get_json()["totalScore"] == 0
    assert post(client, "/api/unlock-all", "").get_json() == {"ok": True}
    assert client.get("/api/levels/2").status_code == 200


def test_api_unknown_routes_and_methods(client):
    assert client.get("/api/nothing").get_json() == {"ok": False, "error": "Unknown API route GET /api/nothing.",
                                                     "field": "path"}
    wrong = client.get("/api/analyze")
    assert wrong.status_code == 404
    assert wrong.get_json()["error"] == "Unknown API route GET /api/analyze."
    assert post(client, "/api/levels", "").status_code == 404
    put = client.put("/api/analyze")
    assert put.status_code == 405
    assert put.get_json() == {"ok": False, "error": "Only GET and POST are supported.", "field": "request"}


def test_static_files_and_traversal(client):
    index = client.get("/")
    assert index.status_code == 200
    assert b"<title>HasseQuest</title>" in index.data
    assert client.get("/js/main.js").status_code == 200
    missing = client.get("/missing.css")
    assert missing.status_code == 404
    assert b"The page /missing.css does not exist." in missing.data
    assert client.get("/../PROJECT_SPEC.md").status_code == 404
    assert client.get("/%2e%2e/PROJECT_SPEC.md").status_code == 404
    assert index.headers["Cache-Control"] == "no-store"
