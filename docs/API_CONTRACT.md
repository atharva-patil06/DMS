# HasseQuest HTTP API contract

This is what the C++ server (`app/api.cpp`, `app/http_server.cpp`) does today, recorded from real responses. The Python/Flask server must match it exactly, because `frontend/` is not changing. Examples are copied from the running C++ server; `...` marks where a long array was cut.

## General rules

| Rule | Value |
|---|---|
| Address | `127.0.0.1` only, default port **8080** |
| Request body | `application/x-www-form-urlencoded` (the frontend uses `URLSearchParams`). `+` means space, `%XX` is decoded. |
| Body limit | 1 MB |
| Success reply | `200`, `Content-Type: application/json; charset=utf-8`, an object with `"ok": true` |
| Error reply | `{"ok": false, "error": "<message>", "field": "<field name>"}` with the status listed per case |
| Key order | The C++ writes keys in the order shown below. The frontend uses `JSON.parse`, so order doesn't matter to it, but Python keeps the same order (Flask's key sorting turned off) so responses can be compared directly. |
| Headers | `Connection: close`, `Cache-Control: no-store` |

### Shared poset fields (used by `/api/analyze`, `/api/bounds`, `/api/check-hasse`)

| Field | Required | Format | Example |
|---|---|---|---|
| `elements` | always | labels separated by commas, spaces or `;`; outer `{}` allowed; blank or `{}` = empty set; labels `[A-Za-z0-9_]{1,6}`, at most 12 | `1,2,3,4,6,12` |
| `mode` | no (default `pairs`) | `pairs`, `matrix` or `rule` | `rule` |
| `relation` | if mode = `pairs` | pairs `(a,b)`, `a<=b`, `a≤b`, `a>b`, separated by `,` `;` or spaces | `1>2;2>4` or `(1,2), 2<=4` |
| `matrix` | if mode = `matrix` | rows separated by `;` or newlines, cells `0`/`1`, spaces and commas ignored | `110;010;111` |
| `rule` | if mode = `rule` | `divisibility`, `subset` or `leq` | `divisibility` |
| `auto_reflexive` | no (default `0`) | `1` adds every missing `(a,a)` and reports it in `notes` | `1` |

A missing required field gives `400 {"ok":false,"error":"The request is missing the field '<name>'.","field":"<name>"}`.

### Shared value shapes

* **Label list:** `["1","2","3"]`
* **Optional label:** a label string, or `null` when it doesn't exist
* **Pair list:** `[["1","2"],["2","4"]]` (each pair is `[smaller, larger]`)
* **Matrix:** `[[1,1,1],[0,1,1],[0,0,1]]` (ints 0/1)
* **Label table** (join/meet): matrix of labels or `null`
* **Step:** `{"title": str, "detail": str, "result": "OK"|"FAIL"|"INFO"|"HEAD"}` plus `"matrix"` (matrix) only when the step has a matrix snapshot. `HEAD` steps start a new section in Show Working.
* **Feedback:** `{"kind": str, "message": str, "from": str, "to": str}`; `kind` is one of `correct`, `redundant`, `unrelated`, `downward`, `missing`, `loop`, `wrong`, `extra`, `info`; `from`/`to` are labels or `""`.
* **Check result block** (used by check-hasse and level check): `accuracy` (int %, rounded half up), `correctEdges`, `wrongEdges`, `missingEdges`, `totalCovers` (ints), `precision`, `recall` (int %), `feedback` (list). For non-edge level types the edge counters are `0` and precision/recall are `0`.

---

## POST /api/analyze

Full analysis of any set and relation. Fields: the shared poset fields.

Reply keys, in order:

| Key | Type | Notes |
|---|---|---|
| `ok` | `true` | |
| `elements` | label list | |
| `matrix` | matrix | after auto-reflexive |
| `notes` | list of str | parser notes (duplicate pairs, auto-added pairs, empty set), then shape notes (empty relation, single element, total order, antichain) |
| `properties` | object | `reflexive`, `symmetric`, `antisymmetric`, `transitive`, each `{"holds": bool, "counterexample": str}` |
| `isEquivalence` | bool | |
| `equivalenceClasses` | list of label lists | **only present when** `isEquivalence` is true |
| `isPoset` | bool | |
| `failedAxiom` | str | `""`, `reflexive`, `antisymmetric` or `transitive` |
| `reason` | str | `""` for a poset |
| `hasCycle` | bool | |
| `closures` | object | `reflexive`, `symmetric`, `transitive` matrices |
| *the keys below appear only when* `isPoset` *is true* | | |
| `isTotalOrder`, `isAntichain` | bool | |
| `covers` | pair list | |
| `levels` | list of int | one per element |
| `minimal`, `maximal` | label lists | |
| `least`, `greatest` | optional label | |
| `height` | int | |
| `longestChain` | label list | bottom to top |
| `width` | int | |
| `largestAntichain` | label list | |
| `lattice` | object | `isLattice` bool, `reason` str, `failPair` (label list of 2, or `null`), `join` label table, `meet` label table |
| `steps` | list of steps | always last |

Step sections (HEAD steps), in order: `Input`, `Relation properties`, `Closures (Warshall's algorithm)`, and for a poset `Hasse diagram: covering relation`, `Special elements`, `Lattice check: lub and glb of every pair`.

Example (`elements=1,2,4&mode=rule&rule=divisibility`):

```json
{"ok":true,"elements":["1","2","4"],"matrix":[[1,1,1],[0,1,1],[0,0,1]],
 "notes":["Every two elements are comparable: this is a total order (a chain), so the Hasse diagram is a straight line."],
 "properties":{"reflexive":{"holds":true,"counterexample":""},"symmetric":{"holds":false,"counterexample":"(1,2) is in R but (2,1) is not."},"antisymmetric":{"holds":true,"counterexample":""},"transitive":{"holds":true,"counterexample":""}},
 "isEquivalence":false,"isPoset":true,"failedAxiom":"","reason":"","hasCycle":false,
 "closures":{"reflexive":[[1,1,1],[0,1,1],[0,0,1]],"symmetric":[[1,1,1],[1,1,1],[1,1,1]],"transitive":[[1,1,1],[0,1,1],[0,0,1]]},
 "isTotalOrder":true,"isAntichain":false,"covers":[["1","2"],["2","4"]],"levels":[0,1,2],
 "minimal":["1"],"maximal":["4"],"least":"1","greatest":"4","height":3,"longestChain":["1","2","4"],
 "width":1,"largestAntichain":["1"],"lattice":{"isLattice":true,"reason":"","failPair":null,"join":[...],"meet":[...]},
 "steps":[{"title":"Input","detail":"","result":"HEAD"}, ...]}
```

Errors: `400` with the `InputError` message and field (`elements`, `relation`, `matrix`, `rule`, `mode`).

## POST /api/bounds

Fields: shared poset fields + `subset` (required, labels like `elements`; repeats counted once; may be empty).

Reply: `ok`, `subset` (label list), `upperBounds`, `lowerBounds` (label lists), `lub`, `glb` (optional labels), `steps` (one HEAD step `Bounds of S = {..}`, one `Candidate x` step per element, then `lub of ...` and `glb of ...`).

```json
{"ok":true,"subset":["2","3"],"upperBounds":["6"],"lowerBounds":["1"],"lub":"6","glb":"1","steps":[{"title":"Bounds of S = {2, 3}","detail":"","result":"HEAD"},{"title":"Candidate 1","detail":"Upper bound? 2<=1 no, 3<=1 no.  Lower bound? 1<=2 yes, 1<=3 yes.","result":"INFO"}, ...]}
```

Errors: `400`, e.g. not a partial order → field `relation`, `"Cannot compute bounds because R is not a partial order. ..."`; unknown subset label → field `subset`.

## POST /api/check-hasse

Fields: shared poset fields + `edges` (required; pairs `a>b;c>d` where `a>b` means b drawn above a; may be empty).

Reply: `ok`, then the check result block, then `score` (int, out of 100, no hints, one attempt) and `passed` (bool, accuracy ≥ 0.999).

```json
{"ok":true,"accuracy":33,"correctEdges":1,"wrongEdges":1,"missingEdges":1,"totalCovers":2,"precision":50,"recall":50,
 "feedback":[{"kind":"correct","message":"2 covers 1: correct edge.","from":"1","to":"2"},
             {"kind":"redundant","message":"Edge 1-4 is redundant. 1 < 2 < 4 already forces it by transitivity. Hasse diagrams omit it.","from":"1","to":"4"},
             {"kind":"missing","message":"Missing edge 2-4: 4 covers 2 (nothing sits strictly between them).","from":"2","to":"4"}],
 "score":33,"passed":false}
```

## GET /api/levels

Reply: `ok`, `totalScore`, `maxScore` (sum of all level points), `levels`: list of `{id, title, type, points, unlocked, completed, stars, bestScore, attempts, hintsUsed}`.

## GET /api/levels/&lt;id&gt;

Reply keys in order: `ok`, `id`, `type`, `title`, `description`, `tip` (the level's `hint:` text or `""`), `points`, `posetTitle` (level title, or the generated title for the boss), `elements`, `matrix`, then **only for** `spot_elements`, `bounds`, `lattice`: `covers`, `levels`; then `pairs` (non-reflexive pairs of R), `relationText` (wire format; reflexive pairs left out except in `fix_relation`), **only for** `bounds`: `subset`; **only for** `boss`: `timeLimit` (180); then `costPercent` (15), `completed`, `stars`, `bestScore`, `attempts`, `hintsUsed`.

Opening the boss level generates a new random poset (6 to 9 elements; divisibility, subset or random) and starts the server-side timer.

## POST /api/levels/&lt;id&gt;/check

Field: `answer` (required). Format by level type:

| Type | `answer` |
|---|---|
| `build_hasse` | `a>b;c>d` |
| `spot_elements` | `minimal:1,2;maximal:12;least:none;greatest:none` |
| `bounds` | `upper:12,36;lower:1,2;lub:12;glb:2` |
| `fix_relation` | the whole new relation, `a>a;a>b;...` |
| `lattice` | `lattice:yes` or `lattice:no;pair:a,b` |
| `boss` | `edges:1>2,2>4;minimal:1;maximal:4;lattice:yes` |

Reply keys in order: `ok`, `passed`, `score`, `stars`, `attempts`, `timeBonus`, `elapsedSeconds`, the check result block, `newlyUnlocked` (list of int), `bestScore`, `totalScore`.

```json
{"ok":true,"passed":true,"score":100,"stars":3,"attempts":1,"timeBonus":0,"elapsedSeconds":0,"accuracy":100,
 "correctEdges":0,"wrongEdges":0,"missingEdges":0,"totalCovers":0,"precision":0,"recall":0,
 "feedback":[{"kind":"correct","message":"Adding (a,d) is needed.","from":"a","to":"d"},{"kind":"info","message":"Your relation is a partial order.","from":"","to":""}],
 "newlyUnlocked":[],"bestScore":100,"totalScore":100}
```

A malformed answer gives `400` (field `answer` or `edges`) and does **not** count as an attempt.

## POST /api/levels/&lt;id&gt;/hint

Reply: `ok`, `number` (1, 2, or 0 when none are left), `text`, `costPercent` (15, or 0 when none are left), `hintsUsed`.

```json
{"ok":true,"number":1,"text":"The minimal elements are {2, 3}: nothing is strictly below them.","costPercent":15,"hintsUsed":1}
```

### Level route errors (checked in this order)

| Case | Status | Body |
|---|---|---|
| id not a number or no such level | 404 | `{"ok":false,"error":"There is no level '99'.","field":"level"}` |
| level locked | 403 | `{"ok":false,"error":"This level is locked. Complete level 1 first.","field":"level"}` |
| unknown action or wrong method | 404 | `{"ok":false,"error":"Unknown level action.","field":"path"}` |
| boss checked or hinted before being opened | 400 | `{"ok":false,"error":"Open the Boss level first to generate its poset.","field":"level"}` |

## GET /api/generate

Query fields: `type` (required). Then:

| `type` | Extra fields | Result |
|---|---|---|
| `divisors` | `n` (default 12) | divisors of n with the divisibility rule |
| `powerset` | `letters` (default `abc`) | all subsets with the subset rule |
| `divisibility`, `subset`, `leq`, `random` | `size` (default 8, 1 to 12) | a random poset |

Reply: `ok`, `type`, `title`, `elements` (one string, e.g. `"10 13 38"` or `"1, 2, 3, 4, 6, 12"` for divisors/powerset), `mode`, `rule`, `relation` (wire format or `""`), `autoReflexive` (bool).

```json
{"ok":true,"type":"leq","title":"Numbers under <=","elements":"10 13 38","mode":"rule","rule":"leq","relation":"","autoReflexive":false}
```

Errors: `400`, e.g. `{"ok":false,"error":"'size' must be a whole number, got 'abc'.","field":"size"}`, `"720 has more than 12 divisors; ..."` (field `n`), unknown type (field `type`).

## GET /api/score

Reply: `ok`, `totalScore`, `maxScore`, `history`: list of `{levelId, title, score, stars, accuracy}` in the order played.

## POST /api/reset and POST /api/unlock-all

Reply: `{"ok":true}`.

## Errors outside the routes

| Case | C++ status and body | Python plan |
|---|---|---|
| Unknown `/api/...` path, or a known path with the wrong method (e.g. `GET /api/analyze`) | 404 `{"ok":false,"error":"Unknown API route GET /api/analyze.","field":"path"}` | identical |
| Bad percent-encoding (`%ZZ`) | 400 `{"ok":false,"error":"Bad percent-encoding in the request.","field":"request"}` | identical |
| Unexpected internal error | 500 `{"ok":false,"error":"The server could not process this request.","field":"request"}` | identical |
| Body over 1 MB | 413 **HTML page** "Request body is too large (limit 1 MB)." | **JSON** 413 `{"ok":false,"error":"Request body is too large (limit 1 MB).","field":"request"}` (see note) |
| HTTP method other than GET/POST | 405 **HTML page** "Only GET and POST are supported." | under `/api/`: **JSON** 405 with the same message, field `request` (see note) |
| Static file not found | 404 HTML page "The page /x does not exist." | identical (HTML) |
| Path containing `..` | 400 HTML page "Invalid path." | Flask refuses it (404); the file is never served |

**Note on the two JSON changes:** the C++ server produces those two errors in its socket layer, before routing, so they come out as HTML. The migration spec asks for JSON errors on oversized bodies and on any bad request. The frontend never sends either kind of request, and `api.js` already turns a non-JSON reply into a friendly message, so the user sees nothing different. Everything else is byte-for-byte the same JSON.
