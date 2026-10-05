# Commit plan: who commits what (Python version)

Every member must have real commits on GitHub, and each person must be able to explain the files they commit. The Python port is split into the same 5 modules as before. Each member works on a branch `feature/<name>-<module>`, makes the small commits listed below **from their own GitHub account**, and opens a pull request into `main`.

Merge in the order Member 1, 2, 3, 4, 5. The modules depend on each other (for example `app/` uses `core/`), so the app and the full test suite work once all five branches are merged. Before each commit, run the tests for your own files, e.g. `python -m pytest -q tests/test_relations.py`. After the last merge, run `python -m pytest -q` on a fresh clone. It should print `81 passed`.

## Step 0: remove the C++ backend (Shivtej Kadlag)

The deletions of the old C++ files (`app/*.cpp`, `core/`, `tests/*.cpp`, `build.bat`, `Makefile`) are already staged; `git status` lists them as `deleted`. Commit them together with the new ignore rules and the migration notes:

```bat
git checkout -b feature/shivtej-remove-cpp
git add .gitignore MIGRATE_TO_PYTHON.md docs/API_CONTRACT.md docs/PORTING_INVENTORY.md
git commit -m "Remove the C++ backend before the Python port; add migration plan and API contract"
```

## Member 1: Atharva Patil (relations, closures, step log, utilities)

Branch: `git checkout -b feature/atharva-relations`

```bat
git add core/__init__.py core/util.py tests/test_util.py
git commit -m "Add Python string helpers (trim, split, strict parse_int) with tests"

git add core/errors.py core/types.py core/steps.py
git commit -m "Add Poset/Step data model, InputError and step-log helpers"

git add core/relations.py tests/test_relations.py
git commit -m "Port relation properties, closures and Warshall's algorithm to Python"
```

## Member 2: Arnav Parawar (POSET, Hasse, lattice)

Branch: `git checkout -b feature/arnav-poset-hasse-lattice`

```bat
git add core/poset.py tests/test_poset.py
git commit -m "Port partial order check, special elements, bounds, chains and antichains"

git add core/hasse.py tests/test_hasse.py
git commit -m "Port cover relation, Hasse levels and the randomized brute-force cross-check"

git add core/lattice.py tests/test_lattice.py
git commit -m "Port lub/glb tables and the lattice test"
```

## Member 3: Shivakiran Dharjane (parsers, Flask server, test set-up)

Branch: `git checkout -b feature/shivakiran-parsers-server`

```bat
git add requirements.txt pytest.ini tests/conftest.py
git commit -m "Add requirements (Flask, pytest), pytest config and shared test helpers"

git add core/parsers.py tests/test_parsers.py
git commit -m "Port input parsers for pairs, matrix and rules with the same messages"

git add app/__init__.py app/server.py run.py
git commit -m "Add Flask server: static files, form decoding, JSON error handlers, run.py"

git add tools/parity_check.py docs/PARITY_REPORT.md
git commit -m "Add C++ vs Python parity check tool and its report"
```

## Member 4: Varad Gaikwad (game, API, levels, generators)

Branch: `git checkout -b feature/varad-game-api`

```bat
git add app/level_loader.py app/generators.py
git commit -m "Port level loader and random poset generators"

git add app/game.py tests/test_game.py
git commit -m "Port answer checkers, scoring, hints and GameSession"

git add app/api.py tests/test_api.py tests/test_data_driven.py
git commit -m "Port API routes; add API and data-driven tests"
```

## Member 5: Shivtej Kadlag (frontend, docs)

The frontend did not change in the port. Shivtej commits the updated documentation.

Branch: `git checkout -b feature/shivtej-docs-python`

```bat
git add README.md docs/architecture.md docs/architecture_diagram.html docs/architecture.png
git commit -m "Update README and architecture diagram for the Python backend"

git add docs/DEMO_SCRIPT.md docs/COMMIT_PLAN.md docs/report docs/screenshots
git commit -m "Update demo script, viva questions, commit plan and report for Python"
```

## If one person has to make the commits for others

Use `--author` so the commit is credited to the right GitHub account (the email must be one registered on that member's GitHub account):

```bat
git commit --author="Arnav Parawar <arnav-email@example.com>" -m "..."
```

Doing it from each member's own account and machine is better: the marking checks contribution, and the viva checks that each person knows their files.
