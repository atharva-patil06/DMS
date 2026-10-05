# HasseQuest: demo script and viva guide

## Before the demo (2 minutes, do it before the evaluator arrives)

1. Open a terminal in the project folder and activate the virtual environment: `venv\Scripts\activate` (the prompt starts with `(venv)`).
2. Run the tests: `python -m pytest -q`. It should end with `81 passed`. Leave this window visible, because it proves the tests pass.
3. Start the app with **one command**: `python run.py`
   * The console prints `HasseQuest running at http://localhost:8080` and the browser opens.
   * **If the port is busy**, run `python run.py --port 8081` and open http://localhost:8081.
   * If the browser doesn't open, type the address yourself.
   * No internet is needed: Flask is already installed in `venv`, and the page loads nothing from the web.
4. In the browser press **Ctrl + +** once or twice so the projector shows large text.
5. Keep the server console visible in a corner: Flask prints one line per request (`"POST /api/analyze HTTP/1.1" 200`), which shows the Python server is doing the work.

## The 5-minute demo (let the evaluator choose the inputs)

| Time | What to do | What to say |
|---|---|---|
| 0:00 | Show the three panels. | "Left is input, centre is the Hasse diagram, right is the step-by-step working. All the maths runs in our Python engine; the browser only draws." |
| 0:30 | **Sandbox with a fresh relation.** Ask the evaluator for a number, e.g. 36. Click **Divisors of** with 36. | "The Python code generated the divisors, ran the rule, checked the axioms, removed transitive edges and laid out the levels." Point at minimal (green), maximal (red), least/greatest (gold ring). Drag a node to show it is interactive; press Auto-layout. |
| 1:15 | Open **Show Working**: the relation matrix, then **Closures (Warshall)**, then **Hasse diagram: covering relation**. | "For every pair we ask: is there c with a < c < b? If yes, the edge is implied by transitivity and is removed." |
| 1:45 | **A failing axiom.** Choose Pairs, ask the evaluator for pairs, or type `(1,2), (2,1), (2,3)` on `1, 2, 3` with auto-reflexive ticked. Analyze. | "Not antisymmetric: (1,2) and (2,1) are both in R but 1 != 2. The app gives the exact counterexample and draws R as a directed graph instead." Then untick auto-reflexive on another relation to show the reflexive message and the "auto-add" explanation. |
| 2:30 | **A non-lattice.** Load example "N shape", or ask the evaluator to invent one. | "{a,b} has no lower bound at all, so its glb does not exist, so it is not a lattice." Open the lub/glb tables in Show Working. Type S = `a, b` and press Compute bounds. |
| 3:15 | **Campaign level live.** Campaign tab, then level 1. Drag 1 to the bottom and 12 to the top, draw the edges and deliberately add the edge 1-12. Submit. | "The redundant edge is red-dashed: 1 < 2 < 12 already forces it by transitivity. Partial credit is correct edges over true plus wrong edges." Delete the edge (click it), resubmit, and show the stars and the unlock. |
| 4:15 | Press **Hint** on the next level; show the Score tab. | "Hints and extra attempts cost points; stars come from accuracy, hints and attempts, all computed on the server." |
| 4:40 | Type rubbish into the elements box, e.g. `1, 2, 2` or a pair with an unknown element. | "Every invalid input gets a clear message naming the bad token. The server never crashes." |

Backup inputs if the evaluator wants more: `Power set of abc`, Random poset with 8 elements, Matrix example, `e, a, b, ab, ac` with the subset rule, `7, 2, 9, 4` with the `<=` rule (a chain, so a straight line).

---

## Viva cheat-sheet (5 likely questions per module)

### Module 1: Relations, closures, step log, utilities (Atharva Patil)

1. **How does Warshall's algorithm compute the transitive closure?**
   Start with W = M(R). For each k from 1 to n, set W[i][j] = W[i][j] OR (W[i][k] AND W[k][j]). After step k, W[i][j] = 1 exactly when there is a path from i to j using only a1..ak in between, so after the last k, W = R+. It runs in O(n^3). See `warshall()` in `core/relations.py`; we save a copy of the matrix after every k for the Show Working panel.
2. **Why a list of lists for the matrix?**
   `R[a][b]` is 1 exactly when (a,b) is in R, so checking a pair is one lookup. Warshall's algorithm works directly on the rows and columns, which is exactly how the textbook writes it, and the matrix is what we display. We use plain lists of 0/1 instead of numpy or sets of pairs so every line is easy to follow.
3. **How do you find a counterexample for transitivity?**
   Three nested loops over a, b, c: if (a,b) and (b,c) are in R but (a,c) is not, we stop and report that triple (`_test_transitive`).
4. **What is the difference between the reflexive closure and the reflexive-transitive closure?**
   The reflexive closure is R plus all (a,a). R* is the transitive closure of that, which is the smallest reflexive and transitive relation containing R. We use R* as the unique best answer in "Fix the Relation".
5. **Why does `add_matrix_step` copy the matrix?**
   Python lists are shared by reference. Without the copy, every Warshall step would point at the same list, and the panel would show the final matrix k times instead of how it changed after each step.

### Module 2: POSET, Hasse and lattice logic (Arnav Parawar)

1. **Walk me through `cover_relation` line by line.**
   It first makes sure R is a partial order (`require_partial_order`). Then, for every a and b with a < b (`strictly_below`), `_find_middle` looks for a c with a < c < b. If one exists, the pair is implied by transitivity and dropped. If none exists, b covers a and we keep the edge. Each decision is added to the step list.
2. **Why is a Hasse diagram drawn without transitive edges?**
   They carry no information: if a < c < b, then a < b follows from transitivity. Leaving them out keeps the diagram readable, and the relation can still be recovered by following upward paths.
3. **Difference between maximal and greatest?**
   Maximal means nothing is strictly above it, and there can be several. Greatest means it is above every element, so it is comparable with everything and unique if it exists. A greatest element is always the only maximal element. In a finite poset the converse also holds (a unique maximal element is greatest), but with several maximal elements there is no greatest one, as in divisibility on {2,3,4,6,9,12,18}.
4. **Is every totally ordered set a lattice?**
   Yes. In a chain any two elements are comparable, so lub(a,b) = max(a,b) and glb(a,b) = min(a,b). Our test `test_lattice_chain_and_single_element_are_lattices` checks this.
5. **How do you compute the height and the width?**
   Height: we order the elements bottom-up and use dynamic programming, where longest chain ending at x = 1 + the maximum over y < x (`longest_chain_ending`). Width: we try all subsets (at most 2^12 = 4096, using a bit mask) and keep the largest one where no two elements are comparable.

### Module 3: Parsers, Flask server, test set-up (Shivakiran Dharjane)

1. **How does a Flask route receive form fields?**
   The browser sends the fields in the request body as `elements=1%2C2&mode=pairs&...`. Inside a route, `request.get_data()` gives that text, and our `parse_form` splits it at `&` and `=` and percent-decodes each part (`%2C` becomes `,`). We decode it ourselves instead of using `request.form` so a broken escape like `%ZZ` gives a clear "Bad percent-encoding" error instead of being silently accepted.
2. **Why does the browser need a server at all?**
   The maths is in Python, and a web page cannot call Python functions directly. The page sends HTTP requests (`fetch`) to our Flask program, which runs the Python code and replies with JSON. Serving from localhost also lets the browser load our HTML, CSS and JS files.
3. **What stops a bad request from crashing the server?**
   Flask error handlers in `server.py`: `InputError` from the maths core becomes a 400 JSON error with the field name, a bad escape becomes 400, a body over 1 MB becomes 413 (Flask's `MAX_CONTENT_LENGTH`), unknown routes become 404, and any other exception becomes a 500 JSON error. The server keeps running in every case.
4. **What is a virtual environment?**
   `python -m venv venv` creates a private folder with its own Python and its own installed packages. `pip install -r requirements.txt` puts the exact Flask and pytest versions we tested into it, without touching the computer's main Python. After that the project runs offline, and every team member gets the same versions.
5. **How does the parser accept `(1,2)`, `1<=2` and `1>2`?**
   First we normalise: turn the Unicode less-or-equal sign into `<=` and remove spaces around `<`, `=`, `>`. Then we scan: a `(` means read up to `)` and split on the comma; otherwise we read a token and split it at `<=` or `>`. Each label must be in A, otherwise the error message names the bad element.

### Module 4: Game mechanics, API, levels, generators (Varad Gaikwad)

1. **How is a drawn Hasse diagram scored?**
   We compare the player's edges with `cover_relation`. Accuracy = correct / (true edges + wrong edges), which combines precision (correct / drawn) and recall (correct / true). Score = points × accuracy, minus 15% per hint and 5% per extra attempt, rounded (exact halves round up). Stars are given only for a fully correct answer.
2. **How do you tell the player *why* an edge is wrong?**
   `_judge_wrong_edge` checks in order: self-loop; b < a (drawn downward); (a,b) not in R (unrelated); or there is a c with a < c < b (redundant by transitivity, naming c). Missing covers get "b covers a: nothing sits strictly between them".
3. **How does the Fix the Relation level know the minimum answer?**
   Any partial order containing R must contain the reflexive-transitive closure R*, so the fewest additions is exactly R* minus R. The level loader also checks that R* is antisymmetric, so the level can be solved by adding pairs only.
4. **How is cheating on the boss timer prevented?**
   The timer in the browser is only for display. The server records `time.time()` when the boss poset is generated, and computes the elapsed time itself when the answer arrives.
5. **How are random posets guaranteed to be partial orders?**
   We shuffle the elements and add random pairs only from earlier to later positions, so there can be no cycle. Then we take the reflexive-transitive closure. A test generates every type and size from 1 to 12 and checks `is_partial_order`.

### Module 5: Frontend UI, docs (Shivtej Kadlag)

1. **Does the JavaScript do any mathematics?**
   No. It collects input, sends it with `fetch` as form fields, and draws the JSON reply. Even the vertical levels in the diagram come from the Python function `hasse_levels`. The JS only spreads nodes sideways and handles dragging.
2. **How does dragging work?**
   On `pointerdown` over a node we remember it. On `pointermove` we convert the mouse position into SVG coordinates (`getScreenCTM().inverse()`) and move the node. If the pointer did not move, it counts as a click instead (select / draw edge / mark).
3. **How is the direction of a drawn edge decided?**
   From the picture: the end drawn lower on screen is the smaller element. So if the player draws 12 below 6 and joins them, the server replies "direction is upward".
4. **Did the frontend change when the backend moved from C++ to Python?**
   No. We first wrote down the exact API (`docs/API_CONTRACT.md`: every route, field and reply key). The Python server was built to match it, and a parity check compared 174 replies from both servers. So the same HTML, CSS and JS work unchanged.
5. **How do you show errors without exposing raw server errors?**
   Every API reply has `ok`. `api.js` turns network failures and non-JSON replies into friendly `{ok:false,error}` objects, and `ui.showError` shows the message in a banner and focuses the input field named in `field`.

### General questions anyone may get

* **Why is `core/` independent of Flask?** The maths should not care how it is shown. `core/` only takes lists and returns results, so it can be tested directly with pytest (no server needed), reused from any other program, and explained without knowing Flask. Only `app/` knows about HTTP and JSON.
* **Why raise `InputError` instead of printing?** The core must not do any I/O. Raising lets the app layer decide how to show the error (JSON with the field name).
* **Why is the empty poset a lattice?** By the definition "every pair has a lub and a glb", there are no pairs, so the condition holds vacuously. We mention that some textbooks require lattices to be non-empty.

---

## Per-member explanation guide (plain language)

* **Atharva Patil: relations and closures.** Given a relation as a grid of 0s and 1s, my code checks the four basic properties and, when one fails, finds a concrete example of the failure. It also builds closures: adding the pairs needed to make a relation reflexive, symmetric or transitive. The transitive one uses Warshall's algorithm, which we show matrix by matrix. I also wrote the small helpers everyone uses (number reading, splitting, the step log).
* **Arnav Parawar: posets, Hasse diagrams and lattices.** Once a relation is known to be a partial order, my code works out its structure: which elements are minimal or maximal, whether a least or greatest element exists, the bounds of any subset, the Hasse diagram edges (only the pairs with nothing in between), the levels for drawing, and whether every pair has a lub and a glb (a lattice). If not, it names the pair that fails.
* **Shivakiran Dharjane: input and the server.** My code turns whatever the user types into a clean set and relation, with clear messages when something is wrong. I also set up the Flask server: it serves the web page, decodes the form fields, and makes sure every error comes back as a friendly JSON message instead of a crash. I set up the tests (pytest) and the tool that compared our Python server with the old C++ one.
* **Varad Gaikwad: the game.** My code defines what each level asks, checks answers by calling the maths core, explains mistakes, gives hints, and computes scores, stars and unlocks. It also reads the level files and generates random posets for the boss level, and the API routes connect each web request to the right function.
* **Shivtej Kadlag: the interface and the docs.** I built the web page: the three-panel layout, the SVG canvas where you drag elements and draw edges, the colour coding, the Show Working panel, and the campaign screens. I also wrote the README, the report and the demo material.
