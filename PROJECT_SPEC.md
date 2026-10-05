# HasseQuest (C++11 / MinGW 6.3, zero third-party libraries): ISE-2 Project Spec (Discrete Mathematics 7MA206)

> **Instructions for Claude Code:** Read this whole file before writing any code. Build the project exactly as specified, in **C++11**, with **no third-party libraries at all** (no Boost, no cpp-httplib, no nlohmann/json, no GoogleTest, no CMake). The team's compiler is **MinGW GCC 6.3 on Windows**, which is what they are taught, so every line must compile there. Where something is marked `TODO(team)`, ask me before assuming. Work in the milestone order in Section 12 and make sure the project **compiles and all tests pass** after each milestone. Write original code; do not copy online templates (see Section 1).

---

## 1. Context and non-negotiable rules

This is a college assessment (S.Y. B.Tech. IT, ISE-2, out of 50 marks). A team of 3 to 4 students builds a **Track A: Gamified Discrete Math Application**. It will be graded on a live demo, a GitHub repo, a 2-page PDF report, and an individual viva where each student must explain the code they wrote.

**Hard rules, each tied to a penalty in the marking sheet:**

| Rule | Penalty if violated |
|---|---|
| Must have a GUI / Web UI (no CLI-only) | -10 marks |
| No hardcoded or single static test case. Any user input must work. | 0 in B2, max 2 in A2 |
| Original work; no unmodified online template | 0 for the entire ISE-2 |
| Every member must have commits on GitHub | lose C4 marks |
| Every member must be able to explain their module | lose D2/D3 marks |

**Therefore:**
- Keep the C++ simple enough that a student can explain every function in a viva. Prefer plain loops, `std::vector`, `std::set`, `std::map`, `std::string` over template tricks, heavy `<algorithm>` chains, or clever one-liners.
- Comment the *why* of each mathematical step, referencing the definition used.
- Never hardcode answers. Levels may be *seeded* from data files, but every checker must work for arbitrary input.
- Because there are no libraries, **all code in the repo is the team's own**, which also helps with the originality rule.

---

## 2. Project concept

**Name:** HasseQuest
**Syllabus topic:** Unit III, Relations, POSETs and Functions (relation properties, partial orders, Hasse diagrams, lattices).
**Track:** A (gamified).

**Pitch:** The player is given a set and a relation (e.g., divisibility on {1,2,3,4,6,12}). They must draw the correct Hasse diagram, identify special elements, or decide whether the poset is a lattice. The C++ mathematics engine validates every move, explains mistakes step by step, and drives scoring and level progression. A **Sandbox/Solver mode** lets anyone enter their own relation and get a full analysis, which satisfies the "accepts any user input" requirement.

> `TODO(team)`: Confirm the topic. If the team picked a different topic, tell Claude Code and Sections 4 to 6 must be rewritten. The architecture, build, rubric mapping, testing and documentation sections still apply.

---

## 3. Tech stack and architecture

**Stack (everything graded as "logic" is C++, with zero dependencies):**
- **Language:** **C++11** (`g++ -std=c++11`), standard library only.
- **Server:** a small **single-threaded HTTP server written by the team** on top of the operating system's sockets (Winsock2 on Windows, with an `#ifdef` POSIX fallback so the code can also be built on Linux/macOS). Serves static files from `frontend/` and answers `/api/...` requests. Binds to `127.0.0.1` only.
- **JSON output:** a tiny hand-written `JsonWriter` class (builds JSON text with correct string escaping). **No JSON parser is needed**: requests from the browser are sent as simple form-encoded text (see 5.5), and the browser's built-in `JSON.parse` reads the responses.
- **Frontend (browser UI):** plain HTML + CSS + vanilla JavaScript, diagrams drawn with SVG. It only draws and sends/receives data; it contains **no mathematics**. The user runs one executable and opens `http://localhost:8080`.
- **Build:** `build.bat` (calls `g++` directly) and a `Makefile` (for `mingw32-make`). No CMake.
- **Tests:** a small test runner **written by the team** (a header with `TEST`/`CHECK` macros, about 40 lines), producing `hq_tests.exe`. Test data in plain text files.

**Forbidden (not available or unreliable on MinGW 6.3 / not taught):**
`std::thread`, `std::mutex`, `std::async`, `std::filesystem`, `std::optional`, `std::variant`, `std::string_view`, `std::make_unique`, `<regex>`, structured bindings, `if constexpr`, generic lambdas (`auto` parameters), `[[nodiscard]]`, inline variables, and **`std::to_string`, `std::stoi`, `std::stod`** (these are missing or broken on some MinGW builds). Use the helpers `toStr(int)` and `parseInt(...)` in `core/include/hq/util.hpp` (built on `std::ostringstream` / `std::istringstream`) instead. No sanitizers (not on MinGW). No non-ASCII characters in console output.

**Three-layer separation (graded under C1, and the diagram must match the code):**

```
┌─────────────────────────────────────────────┐
│  UI layer (frontend/)                       │  HTML/CSS/JS, SVG drawing, drag & drop
│  Talks to the server only via fetch()       │
└──────────────────┬──────────────────────────┘
                   │ HTTP on localhost (form-encoded request, JSON response)
┌──────────────────▼──────────────────────────┐
│  App layer (app/)                           │  http_server (sockets), router,
│  server, api, game, generators, json_writer │  request -> core calls -> JSON,
│                                             │  level loading, scoring
└──────────────────┬──────────────────────────┘
                   │ plain C++ function calls
┌──────────────────▼──────────────────────────┐
│  Math core (core/), namespace hq            │  NO sockets, NO JSON, NO file/console I/O.
│  parsers, relations, poset, hasse,          │  Pure functions on plain structs.
│  lattice, steps, util                       │  Fully unit-testable.
└─────────────────────────────────────────────┘
        Data layer: data/levels/*.txt, tests/data/*.txt (plain "key: value" text)
```

**Rules:**
- `core/` must never include anything from `app/`, sockets headers or `<fstream>`. It exposes plain structs (`Poset`, `StepLog`, result structs). The `app/` layer converts them to JSON.
- Errors in `core/` are reported by throwing `hq::InputError` (derived from `std::runtime_error`, carrying a user-friendly message and the offending field name). Only the `app/` layer catches it and turns it into an error response.

### 3.1 Toolchain notes (MinGW GCC 6.3)

- Compile flags: `-std=c++11 -O2 -Wall -Wextra -Wpedantic`. Link flag for the server on Windows: `-lws2_32`.
- **Milestone 0 (toolchain spike)** verifies all of this on the real machine before project code is written (see Section 12).
- Source files are UTF-8 without BOM; the web page declares `<meta charset="utf-8">`. The "≤" symbol appears only in the web UI.
- Use `.at()` instead of `[]` for vector access inside `core/`, and keep a debug build option `-g -D_GLIBCXX_DEBUG` (bounds-checked containers) in the Makefile.
- If Claude Code is developing on Linux, still compile with `-std=c++11 -pedantic-errors` and never use anything from the forbidden list, so the code is guaranteed to work with GCC 6.3.

### 3.2 The hand-written HTTP server (app/http_server.*)

A deliberately small server, easy to explain in a viva. Requirements:
- Winsock: `WSAStartup`, `socket`, `bind` (to `127.0.0.1:8080`, port overridable by a command-line argument), `listen`, `accept` loop, `recv`, `send`, `closesocket`, `WSACleanup`. Wrap platform differences in one small section guarded by `#ifdef _WIN32`.
- **One request at a time.** After `accept`, set a receive timeout (about 1 to 2 seconds) so idle "pre-connect" sockets opened by browsers cannot block the server; if nothing arrives, close and continue the loop.
- Parse the request line (`GET`/`POST`, path), headers (`Content-Length`), and body (limit 1 MB). Reject anything else with a clear `400`/`405`/`413`.
- Always reply with `Connection: close` and a correct `Content-Length`.
- Static files: map `/` to `frontend/index.html`; serve `.html .css .js .svg .png .ico .txt` with the right `Content-Type` read via `std::ifstream` in binary mode. **Reject any path containing `..`**. Unknown path gives a `404` page.
- Wrap every handler in `try/catch(...)`: a bad request must **never** crash or stop the server.
- Print one short log line per request to the console (method, path, status) so the demo shows it working.
- On startup, print `HasseQuest running at http://localhost:8080` and, on Windows, optionally open the default browser with `ShellExecuteA`/`system("start ...")` (a `--no-browser` flag turns this off).

### 3.3 Core data model

```cpp
// core/include/hq/types.hpp
namespace hq {
struct Poset {                              // set A with relation R
    std::vector<std::string> labels;        // element labels; index i <-> labels[i]
    std::vector<std::vector<int> > R;       // R[i][j] == 1  <=>  (labels[i], labels[j]) in R   (0/1 matrix)
};
struct Step {                               // one line of "Show Working"
    std::string title;
    std::string detail;
    std::string result;                     // "OK", "FAIL", "INFO"
    std::vector<std::vector<int> > matrix;  // optional matrix snapshot (empty if unused)
};
typedef std::vector<Step> StepLog;
}
```
Elements are stored by index internally; labels are used only for I/O. The relation is a 0/1 `int` matrix (not `vector<bool>`), which makes Warshall's algorithm and matrix display trivial and easy to explain. **Labels** are restricted to `[A-Za-z0-9_]`, 1 to 6 characters (this keeps the simple text formats below unambiguous).

### 3.4 Folder structure

```
hassequest/
├── build.bat             # builds hassequest.exe and hq_tests.exe with g++ (Windows)
├── Makefile              # same, for mingw32-make
├── README.md
├── PROJECT_SPEC.md
├── .gitignore            # *.exe, *.o, build/
├── core/
│   ├── include/hq/
│   │   ├── types.hpp
│   │   ├── util.hpp          # toStr, parseInt, trim, split helpers
│   │   ├── errors.hpp        # InputError
│   │   ├── parsers.hpp       # input parsing + validation
│   │   ├── relations.hpp     # reflexive/symmetric/antisymmetric/transitive, closures
│   │   ├── poset.hpp         # partial order check, min/max, greatest/least, bounds
│   │   ├── hasse.hpp         # transitive reduction -> cover relation, level layout
│   │   ├── lattice.hpp       # lub/glb tables, lattice test
│   │   └── steps.hpp         # step-log helpers
│   └── src/                  # matching .cpp files
├── app/
│   ├── main.cpp              # starts the server
│   ├── http_server.hpp/.cpp  # sockets + request parsing + static files (3.2)
│   ├── json_writer.hpp/.cpp  # minimal JSON builder
│   ├── api.hpp/.cpp          # routes: request fields -> core calls -> JSON
│   ├── game.hpp/.cpp         # levels, scoring, hints, session state
│   ├── level_loader.hpp/.cpp # reads data/levels/*.txt
│   └── generators.hpp/.cpp   # random level generation (divisibility, subset, ...)
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js            # fetch wrappers
│       ├── canvas.js         # SVG Hasse diagram drawing + drag & drop
│       ├── ui.js             # panels, steps display, score board
│       └── main.js
├── data/levels/              # level definitions (plain text, see 5.6)
├── tests/
│   ├── mini_test.hpp         # team-written test macros + runner
│   ├── run_tests.cpp         # main(): runs all registered tests, exit code 1 on failure
│   ├── data/                 # test input/expected-output (plain text, see 6)
│   ├── test_util.cpp
│   ├── test_parsers.cpp
│   ├── test_relations.cpp
│   ├── test_poset.cpp
│   ├── test_hasse.cpp
│   ├── test_lattice.cpp
│   └── test_game.cpp         # scoring/feedback and api logic, called directly (no network)
└── docs/
    ├── architecture.md       # Mermaid diagram (also export PNG)
    ├── architecture.png
    ├── screenshots/
    ├── DEMO_SCRIPT.md
    └── report/               # 2-page report source + final PDF
```

`build.bat` and the `Makefile` must build exactly two executables: `hassequest.exe` (all of `core/src/*.cpp` + `app/*.cpp`) and `hq_tests.exe` (all of `core/src/*.cpp` + `tests/*.cpp` + the pieces of `app/` that the game tests need, but **not** `app/main.cpp`). The server executable finds `frontend/` and `data/` relative to the current directory, with a `--root <path>` option to override.

---

## 4. Mathematical specification (Rubric A1 to A4, 15 marks)

Use standard notation. Every definition below must appear in code comments and in the UI's "Theory" panel.

### 4.1 Definitions

Let A be a finite set and R ⊆ A × A a relation.

- **Reflexive:** ∀a ∈ A, (a,a) ∈ R
- **Symmetric:** ∀a,b, (a,b) ∈ R ⇒ (b,a) ∈ R
- **Antisymmetric:** ∀a,b, (a,b) ∈ R ∧ (b,a) ∈ R ⇒ a = b
- **Transitive:** ∀a,b,c, (a,b) ∈ R ∧ (b,c) ∈ R ⇒ (a,c) ∈ R
- **Partial order (POSET):** R is reflexive, antisymmetric, transitive. Written (A, ≤).
- **Equivalence relation:** reflexive, symmetric, transitive (detect and report this too).
- **Comparable:** a, b comparable iff a ≤ b or b ≤ a.
- **Covering relation:** b *covers* a iff a < b and there is no c with a < c < b.
- **Hasse diagram:** the graph of the covering relation, drawn with smaller elements lower, no self-loops, no edges implied by transitivity, no arrowheads (direction is upward).
- **Minimal / maximal element:** no element strictly below / above it.
- **Least / greatest element:** below / above every element (unique if it exists).
- **Upper bound / lower bound** of a subset S ⊆ A.
- **lub (join, ∨) / glb (meet, ∧):** least upper bound / greatest lower bound of {a,b}.
- **Lattice:** a poset where every pair {a,b} has both a lub and a glb.
- **Chain / antichain**, **height** (longest chain length), **width** (largest antichain; brute force is fine for small sets).

### 4.2 Functions to implement (in `core/`, namespace `hq`)

Each function takes a `Poset` (or labels + matrix), appends to an optional `StepLog*` (may be `NULL`), and returns a plain result struct.

1. `PropertyReport checkProperties(const Poset&, StepLog*)` returns reflexive/symmetric/antisymmetric/transitive flags **plus counterexamples** (e.g., "not transitive: (1,2) and (2,3) are in R but (1,3) is not").
2. `PosetVerdict isPartialOrder(const Poset&, StepLog*)` composes the above and says *which axiom failed and why*.
3. `Closures computeClosures(const Poset&, StepLog*)` computes reflexive, symmetric and transitive closure (**Warshall's algorithm**, logging the matrix after each k step).
4. `std::vector<std::pair<int,int> > coverRelation(const Poset&, StepLog*)` computes the transitive reduction: for each (a,b) with a<b, keep it iff no c with a<c<b.
5. `std::vector<int> hasseLevels(const Poset&)` assigns each element a level (length of the longest chain from a minimal element to it) for layout.
6. `SpecialElements specialElements(const Poset&, StepLog*)` returns minimal, maximal, least, greatest.
7. `BoundsResult bounds(const Poset&, const std::vector<int>& subset, StepLog*)` returns upper and lower bounds of subset S, plus lub/glb if they exist.
8. `LatticeReport latticeCheck(const Poset&, StepLog*)` builds the full lub/glb tables and, if not a lattice, names a failing pair and shows why (e.g., "{a,b} has upper bounds {c,d} but no least one").
9. `std::vector<std::vector<int> > toMatrix(const Poset&)` returns the 0/1 relation matrix.
10. `ChainInfo chainsAndAntichains(const Poset&)` returns height, one maximum chain, and one maximum antichain.

### 4.3 Step-by-step reasoning (Rubric A3, 4 marks)

Every analysis function above must write to the `StepLog`, so the UI's "Show Working" panel can render: the relation matrix, Warshall's per-k matrix updates, each cover-relation test ("is there a c with a<c<b? checking c=2... yes -> edge (1,4) removed"), and each lub/glb computation. Nothing should be a black box.

### 4.4 Mathematical edge cases (Rubric A4, 2 marks)

Handle and give a meaningful message for each of these:
- Empty set ∅ (and the empty relation on a non-empty set)
- Single-element set
- Relation containing elements not in A (invalid relation)
- Duplicate elements or duplicate pairs
- Relation that is not a partial order (e.g., symmetric pairs between distinct elements → antisymmetry violated; cycles)
- Poset that is a total order (a chain) → Hasse diagram is a straight line
- Poset that is an antichain (only reflexive pairs) → no edges
- Poset with multiple minimal/maximal elements and no least/greatest
- Posets that are **not** lattices (e.g., the "N" shape or two incomparable maximal elements)
- Reflexive pairs omitted in input: offer an "auto-add reflexive pairs" option and explain it clearly rather than silently changing the input
- Larger sets: cap at 12 elements with a clear message

---

## 5. Game design (Rubric B, 12 marks)

The mathematics must drive the game. Scores, level unlocks and feedback all come from `core/` results.

### 5.1 Modes

**A. Campaign Mode (levels, unlocked in order)**

| Level type | Task | Checked by |
|---|---|---|
| 1. Build the Hasse | Given (A, R), player drags elements into position and draws the covering edges | `coverRelation` |
| 2. Spot the Elements | Click the minimal / maximal / least / greatest elements | `specialElements` |
| 3. Bounds Challenge | Given subset S, pick its upper bounds, lower bounds, lub, glb | `bounds` |
| 4. Fix the Relation | Given a relation that fails an axiom, add or remove the minimum pairs to make it a poset | `isPartialOrder`, `computeClosures` |
| 5. Lattice or Not? | Decide if the poset is a lattice and justify by picking the failing pair | `latticeCheck` |
| 6. Boss Level | A randomly generated poset (6 to 9 elements) with a mix of the above under a timer | `generators` + all of the above |

Suggested level families (seed data and generators): divisibility on divisors of n (e.g., 12, 24, 30, 36, 60), subset inclusion on power sets of {a,b,c} and {a,b,c,d}, "≤" on integers, and custom hand-built posets (including non-lattices).

**B. Sandbox / Solver Mode (this is what proves B2)**
User enters any set and relation (see 5.3). The app runs the full analysis, draws the Hasse diagram, shows all properties with counterexamples, special elements, lattice verdict and the complete Show Working panel. The user can also pick a subset to compute bounds.

### 5.2 Scoring and feedback (driven by the math)

- Base points per level; **partial credit** = fraction of correct cover edges (precision and recall against `coverRelation`).
- Penalties for wrong edges, with *specific math feedback*:
  - Extra edge a-b that is implied by a<c<b → "This edge is redundant. a < c < b already forces it by transitivity. Hasse diagrams omit it."
  - Edge between elements not related → "(a,b) is not in the relation."
  - Missing edge → "b covers a: nothing sits strictly between them."
  - Edge drawn downward → "Direction is upward: smaller below larger."
- Hint system (costs points): hint 1 = the minimal elements; hint 2 = reveals one correct edge with its justification.
- 1 to 3 stars from accuracy, hints used and attempts. Track a running total, level history and best scores (kept server-side in memory for the session; optional save to a local text file).
- Boss level: timer bonus (timer runs in the frontend; the server validates the final score).

### 5.3 Input methods (any input must work)

1. **Pair list:** `(1,2), (1,4), (2,4)` or `1<=2, 1<=4`
2. **Matrix input:** editable 0/1 grid generated for the elements entered
3. **Rule-based:** choose `divisibility` or `subset inclusion` or `≤` on a user-entered set (e.g., "divisors of 48", or a custom set of integers; subset inclusion uses element labels as sets of letters, e.g., `a`, `ab`, `abc`, with the empty set written `e`)
4. **Click-to-build** in the UI

### 5.4 UI requirements (Rubric B1, B3)

- Clean, intuitive layout: left = controls and input, centre = SVG Hasse canvas, right = Show Working / Theory / Score panels.
- Hasse diagram: nodes in layers by level, smaller at the bottom, edges as plain lines, nodes labelled, **draggable**, auto-layout button that spreads nodes in each level without overlap.
- Colour-code: minimal (green), maximal (red), least/greatest (gold ring), selected subset (blue), wrong edge (red dashed), correct edge (green flash).
- Large readable fonts (this will be a live demo on a projector).
- Clear error banners for invalid input. No raw server errors ever shown.
- A "Load example" dropdown for quick demos, but examples must go through the same code path as user input.

### 5.5 HTTP API (form-encoded requests, JSON responses)

Requests are `POST` with `Content-Type: application/x-www-form-urlencoded` (the browser builds them with `URLSearchParams`); the server percent-decodes the fields. No JSON parsing in C++.

| Route | Request fields | Purpose |
|---|---|---|
| `POST /api/analyze` | `elements=1,2,3,4` `mode=pairs\|matrix\|rule` plus `relation=1>2;2>3` (pairs) or `matrix=0110;0010;...` (rows separated by `;`) or `rule=divisibility\|subset\|leq`, `auto_reflexive=0\|1` | Full analysis of any user-supplied set and relation |
| `POST /api/bounds` | same poset fields + `subset=a,b` | Bounds, lub, glb of a chosen subset |
| `POST /api/check-hasse` | same poset fields + `edges=a>b;c>d` (player's drawn edges, `a>b` = b above a) | Validate edges against `coverRelation`, return feedback and score |
| `GET /api/levels` / `GET /api/levels/<id>` | none | Level list and details |
| `POST /api/levels/<id>/check` | `answer=...` (format depends on level type) | Check an answer for any campaign level type |
| `GET /api/generate?type=divisibility&size=8` | query string | Generate a random level or poset |

Pair notation in pair mode: input boxes accept `(a,b)` or `a<=b`; the frontend converts to the `a>b;` wire format. All responses: `{"ok":true, ...}` or `{"ok":false,"error":"<message>","field":"<input field>"}` with an appropriate HTTP status.

### 5.6 Level file format (data/levels/*.txt)

Plain text, one `key: value` per line, blank line or EOF ends the level. The loader must reject malformed files with a clear message.

```
id: 1
type: build_hasse
title: Divisors of 12
elements: 1 2 3 4 6 12
rule: divisibility
points: 100
```
A level may use `pairs: 1>2 1>3 ...` instead of `rule:`. Other keys: `subset:`, `hint:`, `unlock_after:`.

---

## 6. Input validation, error handling and testing (Rubric C2)

**Validation (in `core/parsers.cpp`, used by every route):**
- Reject unparsable text with a message that shows the offending token and an example of the correct format.
- Reject pairs with elements not in A; reject duplicate elements with a message; trim whitespace; labels must match `[A-Za-z0-9_]{1,6}`.
- Enforce the 12-element limit with a friendly message. Matrix input must be square and match the element count.
- Malformed requests (missing fields, bad percent-encoding, oversized bodies) produce clear error responses, never crashes.

**Memory and robustness:** no raw `new`/`delete`, use standard containers and RAII. Check indices before use (`.at()` in `core/`). The full test suite must also pass in a build with `-g -D_GLIBCXX_DEBUG`.

**Testing (team-written runner, no GoogleTest):**
- `tests/mini_test.hpp` provides `TEST(name) { ... }` (self-registering), `CHECK(cond)`, `CHECK_EQ(a, b)`, and a runner in `run_tests.cpp` that prints each failure with file and line, prints a final `X passed, Y failed`, and returns a non-zero exit code on any failure.
- At least **40 test cases overall**. Include **test data in `tests/data/*.txt`** (plain `key: value` blocks separated by blank lines, e.g. `elements: 1 2 3` / `relation: 1>2 2>3` / `expect_poset: no` / `expect_failed_axiom: reflexive` / `expect_cover: 1>2 2>3`), read by a data-driven test that loops over all blocks. The data must cover: each property true/false, every edge case in 4.4, divisibility and subset posets, non-lattices, parser failures, and the scoring/feedback logic for `check-hasse`.
- Include a regression test confirming that a *redundant* transitive edge is judged **wrong**.
- Include a randomized cross-check: generate random posets (fixed `std::srand` seed for repeatability) and verify `coverRelation` against a separate naive brute-force implementation written inside the test file.
- README must document: `build.bat` (or `mingw32-make`), then `hq_tests.exe`, then `hassequest.exe`.

---

## 7. Code quality (Rubric C3)

- Meaningful names (`coverPairs`, `upperBounds`, not `x1`, `v2`). Consistent naming: `camelCase` functions, `PascalCase` types, one style throughout.
- Header comment on every function: definition used, inputs, outputs.
- Compile with no warnings under `-Wall -Wextra -Wpedantic`.
- Small functions (aim < 30 lines). No duplicated logic between routes. Use `const` and references appropriately; no global mutable state outside the game session object.
- Comments explain the mathematics, not the syntax.

---

## 8. GitHub repository (Rubric C4)

README.md must contain: title, one-paragraph description, features, screenshots (from `docs/screenshots/`), architecture diagram, **setup steps** (MinGW/g++ requirement, how to build with `build.bat` or `mingw32-make`, how to run, how to open the browser, how to run tests), usage guide for each mode, folder structure, **team members and who built which module**, and the syllabus unit covered. Include a `.gitignore` (executables, object files, IDE files).

Repo must also contain: all code, `tests/data/`, screenshots, `docs/report/` PDF.

**Team workflow so every member has real commits:**
- One branch per member (`feature/<name>-<module>`), merge via pull request.
- Suggested module split for 4 members (adapt to team size):

| Member | Module | Files |
|---|---|---|
| `TODO(team)` Member 1 | Relations, closures, step log, util | `core/*/relations.*`, `steps.*`, `util.*`, `tests/test_relations.cpp`, `test_util.cpp` |
| `TODO(team)` Member 2 | POSET / Hasse / lattice logic | `core/*/poset.*`, `hasse.*`, `lattice.*`, their tests |
| `TODO(team)` Member 3 | Parsers, game mechanics, API, JSON, server | `core/*/parsers.*`, `app/*`, `data/levels`, `tests/test_game.cpp`, `mini_test.hpp` |
| `TODO(team)` Member 4 | Frontend UI, build scripts, docs | `frontend/*`, `build.bat`, `Makefile`, README, report |

- Claude Code: tell me which member's module each file belongs to and **do not commit everything in one giant commit**. Prepare small, descriptive commits per module so each person can commit their own part. Do not push to the remote; I will do that.

---

## 9. Two-page technical report (Rubric C5)

Generate the source in `docs/report/report.md` and export a **PDF, strictly ≤ 2 pages**. Required sections:

1. Title, team members, course, date
2. Problem statement and objective
3. Mathematical formulation (key definitions, algorithms: Warshall, transitive reduction, lub/glb)
4. System architecture (embed the diagram)
5. Game mechanics and scoring
6. Implementation details and tech stack (C++11, MinGW GCC 6.3, Winsock HTTP server written by the team, vanilla JS/SVG frontend, no external libraries)
7. Testing and results (number of tests, edge cases handled)
8. Screenshots (1 to 2 small)
9. Individual contributions table
10. Conclusion and future work

Tight formatting: small margins, 10pt font. Verify the page count after generation.

---

## 10. Demo and viva readiness (Rubric D, 10 marks)

Create `docs/DEMO_SCRIPT.md` containing:
- A 5-minute demo flow that uses **live inputs the evaluator can choose**: Sandbox with a fresh relation, one failing-axiom case, one non-lattice, then a campaign level played live. Include how to start the server (one command) and a fallback if the port is busy (`hassequest.exe 8081`).
- A viva cheat-sheet: for each module, 5 likely questions with short answers (e.g., "Why is a Hasse diagram drawn without transitive edges?", "How does Warshall's algorithm compute the transitive closure?", "Is every totally ordered set a lattice?", "Difference between maximal and greatest?", "Walk me through `coverRelation` line by line", "Why did you store the relation as a 0/1 matrix?", "What does `const&` do in this function?", "How does your server accept a request: socket, bind, listen, accept?", "Why does the browser need a server at all?").
- A per-member explanation guide: what each member's module does, in plain language.

---

## 11. Definition of done (rubric checklist)

Claude Code: before declaring the project finished, verify and tick each item.

- [ ] **A1** Definitions and notation correct and shown in the Theory panel
- [ ] **A2** Correct output for arbitrary input (randomized cross-check against brute force passes)
- [ ] **A3** "Show Working" displays matrices, Warshall steps, cover tests, lub/glb computations
- [ ] **A4** All edge cases in 4.4 handled with messages
- [ ] **B1** Clean web UI, Hasse diagram clearly drawn, draggable nodes
- [ ] **B2** Sandbox accepts any set and relation via 3+ input methods; no hardcoded cases
- [ ] **B3** Campaign levels, scoring and feedback all computed by `core/`
- [ ] **C1** Layers separated (`core/` has no socket/file/JSON code); `docs/architecture.png` matches the actual code
- [ ] **C2** Validation messages everywhere; 40+ tests pass in `hq_tests.exe`; test data in `tests/data/`; passes with `-D_GLIBCXX_DEBUG`
- [ ] **C3** Readable names, header comments, no compiler warnings
- [ ] **C4** README complete; small per-module commits prepared
- [ ] **C5** 2-page PDF report, within the limit
- [ ] **D** `docs/DEMO_SCRIPT.md` with viva Q&A and module walkthroughs
- [ ] Builds and runs from a clean clone using only README steps, on **MinGW GCC 6.3** with `build.bat` (and `mingw32-make`), with no downloads and no internet
- [ ] Compiles cleanly with `-std=c++11 -pedantic-errors`; nothing from the forbidden list in Section 3 is used
- [ ] The server survives malformed requests and a browser that opens idle connections

---

## 12. Build order (milestones)

0. **Toolchain spike (do this FIRST, before any project code):** run `g++ --version` and report it. Compile and run, with `-std=c++11 -Wall -Wextra -Wpedantic`: (a) a hello-world using `std::vector`, `std::map`, `std::ostringstream`, an exception and a `typedef`'d `vector<vector<int> >`; (b) a tiny Winsock program linked with `-lws2_32` that listens on `127.0.0.1:8080` and answers one browser request with a static page. Report the results to me before continuing. If something does not compile on the team's compiler, adapt the code (not the compiler) and tell me what you changed.
1. **Scaffold:** folder structure, `build.bat`, `Makefile`, `mini_test.hpp` + `run_tests.cpp` with one passing test, and the server serving `frontend/index.html`.
2. **Math core + tests:** util → errors → types → parsers → relations → poset → hasse → lattice → steps. Write tests alongside each function.
3. **App layer:** JSON writer, routes in 5.5, game/scoring logic, level loader, game tests.
4. **Frontend Sandbox mode:** inputs, diagram rendering, Show Working panel.
5. **Game layer:** campaign levels, hints, feedback, boss level, generators.
6. **Polish:** styling, error banners, projector-friendly fonts, screenshots.
7. **Docs:** architecture diagram, README, report PDF, demo script.
8. **Final audit:** run through Section 11 and report any unchecked items honestly.

---

## 13. Open questions (ask me before building)

1. `TODO(team)` Confirm topic = Unit III (Hasse/POSET/lattice), or specify another.
2. `TODO(team)` Team size and member names (for the module table and README).
3. `TODO(team)` Which IDE or terminal does the team use with MinGW (Code::Blocks, Dev-C++, plain terminal)? Should `build.bat` also come with a Code::Blocks project file?
4. `TODO(team)` Any required theme, college branding, or naming for the app?
