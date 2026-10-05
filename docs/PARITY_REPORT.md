# Parity report: Python backend vs the original C++ backend

Run on 5 October 2026 with `tools/parity_check.py`, comparing the C++ `hassequest.exe` (port 8080) with `python run.py` (port 8081). Both started from fresh sessions.

## What was compared

**174 requests**, sent in the same order to both servers:

* `POST /api/analyze` and `POST /api/bounds` for every one of the 32 blocks in `tests/data/posets.txt`
* `POST /api/check-hasse` for every one of the 10 blocks in `tests/data/hasse_checks.txt`
* 13 extra analyze inputs covering every input notation and every parser error
* bounds and check-hasse error cases
* every `/api/generate` type, including errors
* a whole campaign session: locked/missing levels, unknown actions, details of every level, hints (including running out of hints), right and wrong answers for every level type, malformed answers, the boss level, unlocks and the final score board

Replies were compared as parsed JSON (key order and whitespace ignored), plus the HTTP status. Randomly generated posets and the boss poset were compared by their keys only, because their contents are random by design.

## Result

**171 of 174 replies are identical.** The remaining 3 are the same scoring case, and the Python result is the correct one:

| Request | C++ | Python |
|---|---|---|
| Level 6, 2nd attempt with 1 hint, accuracy 25% | score 7 | score **8** |
| Level 11, 3rd attempt with 1 hint, accuracy 50% | score 37 | score **38** |
| `GET /api/score` | history contains the two scores above | same, with 8 and 38 |

**Why:** in both cases the formula gives an exact half. Level 6: 150 × 0.25 − 15% − 5% = 37.5 − 22.5 − 7.5 = **7.5**, which rounds half up to 8. The C++ exe is a 32-bit MinGW build that keeps floating-point intermediates in 80-bit x87 registers. There, 150 × 0.05 is 7.5000000000000004, so the score became 7.4999999999999996 and rounded down to 7. Python computes the penalties as a whole-number percentage first, so the result is exact.

**Decision (agreed with the team on 5 October 2026):** keep Python's result, which matches the documented scoring formula. `tests/test_game.py` contains `compute_score(150, 0.25, 1, 2) == 8` so this can't change by accident.

## Other intentional differences

These come from `docs/API_CONTRACT.md`, approved before porting, and the frontend never triggers them:

* A body over 1 MB returns JSON `413 {"ok":false,"error":"Request body is too large (limit 1 MB).","field":"request"}` instead of an HTML page.
* An HTTP method other than GET/POST on `/api/...` returns JSON 405 instead of an HTML page.

## Browser smoke test

The same automated browser run used for the C++ app was repeated against the Python server: real mouse drags and clicks in headless Edge. It covered building a Hasse diagram with a redundant edge (red-dashed, with the transitivity explanation), deleting the edge and passing, Spot the Elements, Bounds, Fix the Relation, Lattice with a hint, the boss level with its timer, matrix input, bounds in the Sandbox, error banners, click-to-build, practice mode, and the Show Working panel with Warshall's matrices. Every result matched the C++ run, and there were no JavaScript errors.
