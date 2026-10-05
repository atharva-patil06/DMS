# HasseQuest: Port the Backend from C++ to Python (ISE-2, Discrete Mathematics 7MA206)

> **Status (5 October 2026): done.** The backend is now Python + Flask. Results are in `docs/PARITY_REPORT.md`, the API in `docs/API_CONTRACT.md`, and the C++-to-Python function mapping in `docs/PORTING_INVENTORY.md`. Decisions made with the team: Python 3.14.5 on the demo laptop (Flask 3.1.3, pytest 9.1.1); oversized bodies and non-GET/POST methods answer with JSON errors; exact-half scores round up as the formula says (the old 32-bit C++ build rounded 3 cases down); `legacy_cpp/` deleted after parity passed (the C++ code is still in the git history).

> **Instructions for Claude Code:** The HasseQuest app already works (C++ backend + HTML/CSS/JS frontend). Your job is to **change the tech stack only**: replace the C++ backend with a **Python** backend, keep the existing **HTML + CSS + JavaScript frontend**, and keep **all behaviour identical**. Read this whole file first. Do not add, remove or redesign any game mode, level, scoring rule or UI feature. Where something is marked `TODO(team)`, ask me before assuming.

**Precedence:** `PROJECT_SPEC.md` is still the source of truth for the **mathematics (Section 4), game design and scoring (Section 5), rubric rules (Section 1), report, demo and viva requirements (Sections 8 to 11)**. This file **replaces** its technology choices (Section 3, 3.1 to 3.4, the C++ parts of Sections 6, 7 and 12). Wherever `PROJECT_SPEC.md` says C++, `g++`, `build.bat`, Winsock, `mini_test.hpp` or `-std=c++11`, follow this file instead.

---

## 1. Why and what

The team wants the project in Python, JavaScript, CSS and HTML, using **familiar Python tools only**. The assessment rules still apply (Section 1 of `PROJECT_SPEC.md`): a GUI/Web UI is required, no hardcoded cases, original code, every member has commits and can explain their module in the viva.

**What changes:** everything in `core/` and `app/` (currently C++), the build, the test runner, the server.
**What does NOT change:** `frontend/` (HTML, CSS, JS), `data/levels/*.txt`, `tests/data/*.txt`, the HTTP API, all user-facing messages, all scoring numbers, all maths results and step-by-step logs.

---

## 2. Tech stack (familiar tools only)

| Part | Use | Notes |
|---|---|---|
| Language | **Python 3**, standard library for all maths | Target **3.8+** syntax so it runs on older student installs. No `match` statements, no walrus operator (`:=`), no `X \| Y` type unions. |
| Web server | **Flask** | Plain `@app.route` functions. No blueprints, no async, no FastAPI/pydantic, no Flask extensions. |
| Tests | **pytest** | Plain `assert` tests. |
| HTTP in scripts (optional parity check) | `requests` or `urllib` | Only for `tools/parity_check.py`. |
| Environment | `venv` + `pip install -r requirements.txt` | `requirements.txt` has only `Flask` and `pytest` (pin versions that work on the team's Python). |
| Frontend | Existing HTML + CSS + vanilla JS | Unchanged. |

**Do not use:** numpy, pandas, networkx, SQLAlchemy, Docker, type-checkers as a requirement, decorators or metaclasses beyond Flask's `@app.route`, or anything the team would not recognise from a Python course. Keep the maths in **plain Python lists, dicts, sets and loops** so every function is easy to explain line by line in the viva. Light type hints and docstrings are welcome. Avoid dense one-line comprehension chains for the core algorithms; a short list comprehension is fine.

---

## 3. Architecture (unchanged three layers)

```
frontend/ (HTML/CSS/JS, unchanged)
      │  HTTP on localhost (form-encoded request, JSON response)
app/  (Flask routes, game logic, level loader, generators)
      │  plain Python function calls
core/ (pure maths: no Flask, no file I/O, no printing)
      Data: data/levels/*.txt, tests/data/*.txt  (unchanged plain "key: value" files)
```

**Rules:**
- `core/` must never import `flask`, `os`, `json` or open files. It exposes plain classes/dicts/lists and a step log.
- Errors in `core/` are raised as `InputError(message, field)` (a subclass of `Exception`). Only `app/` catches it and converts it to an error response.
- No global mutable state except one `GameSession` object (single local player, no cookies, no Flask `session`).

Module owners from `PROJECT_SPEC.md` Section 8 stay the same; only the file extensions change (e.g., `relations.cpp` → `relations.py`).

---

## 4. Porting rules (behaviour must be identical)

1. Read the existing code first; write `docs/API_CONTRACT.md`; the Python server must match it exactly.
2. Same function behaviour: same inputs, outputs, step logs and ordering.
3. Same text: every user-facing string copied exactly.
4. Same numbers: scoring, partial credit, hint penalties, star thresholds, timer bonus, 12-element cap.
5. Same data formats: level files, test data files, label rule, wire formats.
6. Same port and binding: default 8080, `127.0.0.1` only, `--port` option; `/` serves `frontend/index.html`; `..` path traversal impossible.
7. Same error behaviour: `{"ok": false, "error": "...", "field": "..."}`, a bad request never crashes the server or returns an HTML error page; `MAX_CONTENT_LENGTH` 1 MB.
8. `Poset` keeps `labels: list[str]` and `R: list[list[int]]` (0/1 matrix).
9. Do not change the frontend.
10. Do not add features.

## 5. Function name mapping

`snake_case` functions, `PascalCase` classes: `checkProperties` → `check_properties`, `isPartialOrder` → `is_partial_order`, `computeClosures` → `compute_closures`, `coverRelation` → `cover_relation`, `hasseLevels` → `hasse_levels`, `specialElements` → `special_elements`, `bounds` → `bounds`, `latticeCheck` → `lattice_check`, `toMatrix` → `to_matrix`, `chainsAndAntichains` → `chains_and_antichains`, `hq::InputError` → `core.errors.InputError`, `StepLog*` → optional `steps=None` list, `JsonWriter` and `http_server.cpp` replaced by Flask, `std::pair<int,int>` → tuple. Full list: `docs/PORTING_INVENTORY.md`.

## 6. Testing

Every C++ test ported to pytest (at least as many, never fewer than 40); the data-driven test reads the same `tests/data/*.txt`; keep the redundant-edge regression test and the randomized `cover_relation` cross-check; `test_api.py` uses `app.test_client()` for every route and error case; run with `python -m pytest -q`; optional `tools/parity_check.py` against the old C++ server.

## 7. Milestones

0. Environment check · 1. Inventory and API contract · 2. Port `core/` module by module · 3. Port `app/` · 4. Frontend smoke test · 5. Parity check · 6. Docs (README, architecture diagram, report ≤ 2 pages, demo script with Python/Flask viva questions, module table) · 7. Clean-up of `legacy_cpp/` (with the team's approval) · 8. Final audit.

## 8. Code quality and git

PEP 8, `snake_case`, meaningful names, a docstring on every function stating the definition used, comments that explain the mathematics, small functions, no duplicated logic, student-explainable code. Small per-module commits so every member commits their own part; do not push.

## 9. Definition of done

- [x] Frontend, `data/levels` and `tests/data` unchanged
- [x] Every route in `docs/API_CONTRACT.md` behaves like the C++ version (171/174 identical; 3 exact-half scores now round up, by decision)
- [x] Python tests ≥ C++ tests (81 vs 67), all passing with `python -m pytest -q`
- [x] Every data block in `tests/data/*.txt` passes
- [x] All modes and levels work in the browser
- [x] Server never crashes on bad input; errors come back as JSON
- [x] `core/` imports no Flask, file or JSON modules
- [x] No C++ left in the active code
- [x] README, architecture diagram, 2-page report and demo script updated for Python
- [x] Runs from a clean clone with: create venv, `pip install -r requirements.txt`, `python run.py`
- [x] Runs offline once dependencies are installed
- [x] Small per-module commits prepared (`docs/COMMIT_PLAN.md`), with the owner of each module noted
