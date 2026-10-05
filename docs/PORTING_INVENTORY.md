# C++ to Python porting inventory

Every C++ function and its Python target. Names use `snake_case`; public functions keep the same meaning, inputs, outputs and step-log text. "(private)" means a `static` helper in the C++ file, which becomes a module-level function starting with `_` in Python. Owners are unchanged from `README.md`.

## core/ (owner in brackets)

| C++ file | C++ function | Python target |
|---|---|---|
| util.cpp [Atharva] | `toStr` | not needed (`str(n)`) |
| | `parseInt` | `util.parse_int(text)` returns `int` or `None`. Same strict rules as the C++: optional sign, digits only, no trailing text, must fit in a 32-bit int. (Python's `int()` alone would also accept `1_000` and other forms the C++ rejects.) |
| | `trim`, `split`, `splitWhitespace`, `join` | `util.trim`, `util.split` (keeps empty pieces, trims each), `util.split_whitespace`, `", ".join(...)` |
| | `isValidLabel`, `isAllDigits`, `containsInt` | `util.is_valid_label`, `util.is_all_digits` (ASCII digits only), `x in list` |
| errors.cpp [Atharva] | `InputError(message, field)`, `field()` | `errors.InputError(message, field)` subclass of `Exception`, attribute `.field`, `str(e)` is the message |
| types.hpp [Atharva] | `Poset {labels, R, size(), related()}` | `types.Poset` class: `labels` (list of str), `R` (list of lists of int), `size()`, `related(a, b)` |
| | `Step`, `StepLog`, `Matrix`, `IndexPair`, `PairList`, `MAX_ELEMENTS = 12` | `types.Step` (title, detail, result, matrix list, empty if unused), step log = plain `list`, pairs = tuples `(a, b)`, `MAX_ELEMENTS = 12` |
| steps.cpp [Atharva] | `zeroMatrix`, `addStep`, `addMatrixStep`, `labelOf`, `pairText`, `setText` | `steps.zero_matrix`, `steps.add_step(steps, ...)`, `steps.add_matrix_step`, `steps.label_of`, `steps.pair_text`, `steps.set_text` (each does nothing when `steps is None`, like `StepLog* = NULL`) |
| parsers.cpp [Shivakiran] | `PosetInput`, `ParsedPoset` | `parsers.PosetInput`, `parsers.ParsedPoset` classes |
| | `parseElements`, `indexOfLabel`, `parsePairs`, `parseMatrix`, `ruleMatrix`, `parseSubset`, `buildPoset`, `divisorLabels`, `powerSetLabels`, `pairsToText` | `parse_elements`, `index_of_label`, `parse_pairs`, `parse_matrix`, `rule_matrix`, `parse_subset`, `build_poset`, `divisor_labels`, `power_set_labels`, `pairs_to_text` |
| | (private) `normaliseElementText`, `isPairSeparator`, `isComparisonChar`, `normalisePairText`, `pairFormatHelp`, `splitComparison`, `lookUpPair`, `readParenPair`, `addUniquePair`, `cleanMatrixRow`, `labelsAsNumbers`, `lettersOf`, `subsetMatrix`, `relationFromInput`, `addReflexivePairs` | same names in `snake_case` with a leading `_` |
| relations.cpp [Atharva] | `PropertyCheck`, `PropertyReport`, `Closures` | classes in `types.py` |
| | `checkProperties`, `computeClosures`, `warshall`, `toMatrix`, `equivalenceClasses` | `check_properties`, `compute_closures`, `warshall`, `to_matrix`, `equivalence_classes` |
| | (private) `logProperty`, `testReflexive`, `testSymmetric`, `testAntisymmetric`, `testTransitive`, `newPairsText` | `_log_property`, `_test_reflexive`, ... |
| poset.cpp [Arnav] | `PosetVerdict`, `SpecialElements`, `BoundsResult`, `ChainInfo` | classes in `types.py`; "no element" is `None` instead of the C++ `-1` |
| | `isPartialOrder`, `requirePartialOrder`, `strictlyBelow`, `comparable`, `specialElements`, `bounds`, `chainsAndAntichains`, `longestChainEnding` | `is_partial_order`, `require_partial_order`, `strictly_below`, `comparable`, `special_elements`, `bounds`, `chains_and_antichains`, `longest_chain_ending` (returns `(length, previous)` instead of using an output parameter) |
| | (private) `findCycle`, `classifyShape`, `strictlyBelowSet`, `strictlyAboveSet`, `findExtreme`, `logExtreme`, `isBoundOf`, `extremeOfSet`, `logBest`, `bottomUpOrder`, `isAntichain` | `_find_cycle`, `_classify_shape`, ... (`_is_bound_of` returns `(ok, reasoning)` instead of an output parameter) |
| hasse.cpp [Arnav] | `coverRelation`, `hasseLevels`, `containsPair` | `cover_relation`, `hasse_levels`, `(a, b) in pairs` |
| | (private) `findMiddle` | `_find_middle` returns `(c, tried)` |
| lattice.cpp [Arnav] | `LatticeReport`, `latticeCheck`, `isFailingPair` | `types.LatticeReport`, `lattice_check`, `is_failing_pair` |
| | (private) `missingReason`, `recordFailure`, `boundText` | `_missing_reason`, `_record_failure`, `_bound_text` |

## app/

| C++ file | C++ function | Python target |
|---|---|---|
| level_loader.cpp [Varad] | `Level`, `parseLevels`, `loadLevels`, `levelInput`, `validateLevel`, `isKnownLevelType` (+ private `levelError`, `numberValue`, `applyKey`, `checkRequiredKeys`, `validateFixLevel`, `readWholeFile`, `checkUniqueIds`) | `level_loader.Level`, `parse_levels`, `load_levels`, `level_input`, `validate_level`, `is_known_level_type` (+ `_level_error`, ...). Errors raise `LevelFileError` with the same messages. |
| generators.cpp [Varad] | `randomInt`, `countDivisors`, `generatePoset` (+ private `divisibilityPoset`, `subsetPoset`, `leqPoset`, `randomPoset`) | `random_int` (wraps `random.randint`), `count_divisors`, `generate_poset` (+ `_divisibility_poset`, ...). Same algorithms; the random numbers themselves differ from C++ `std::rand`, which is fine since they're random anyway. |
| game.cpp [Varad] | `Feedback`, `CheckResult`, `checkHasseEdges`, `checkSpotElements`, `checkBoundsAnswer`, `checkFixRelation`, `checkLatticeAnswer`, `checkBossAnswer`, `parseAnswerSections`, `computeScore`, `computeStars`, constants | `check_hasse_edges`, `check_spot_elements`, `check_bounds_answer`, `check_fix_relation`, `check_lattice_answer`, `check_boss_answer`, `parse_answer_sections`, `compute_score`, `compute_stars`, `HINT_COST_PERCENT = 15`, `MAX_HINTS = 2`, `BOSS_TIME_LIMIT_SECONDS = 180` |
| | (private) `makeFeedback`, `judgeWrongEdge`, `addMissingEdges`, `computeEdgeAccuracy`, `sectionValue`, `answerSet`, `answerElement`, `setSimilarity`, `optionalLabel`, `judgeExtremeSet`, `judgeExtremeElement`, `judgeBoundSet`, `judgeBest`, `whyRequired`, `FixCounts`, `judgeFixPair`, `judgeFailingPair` | `_make_feedback`, `_judge_wrong_edge`, ... |
| | `Game` class, `LevelProgress`, `HistoryEntry`, `LevelView`, `LevelOutcome`, `HintResult` | `GameSession` class (the one piece of mutable state) and the same result classes |
| api.cpp [Varad] | `Api::analyze`, `boundsRoute`, `checkHasse`, `levelList`, `levelDetails`, `levelCheck`, `levelHint`, `generate`, `score`, `route`, `levelRoute`, `handle` | one Flask `@app.route` function per route in `api.py`; each builds a dict and returns it as JSON |
| | (private) `writeLabels`, `writeOptionalLabel`, `writePairs`, `writeMatrix`, `writeLabelTable`, `writeSteps`, `writeFeedback`, `writeProperty`, `writeDiagram`, `writePropertiesSection`, `writePosetSection`, `writeLatticeSection`, `writeCheckResult`, `writeProgress`, `addShapeNotes`, `visiblePairs`, `maxScore`, `percent`, `requireField`, `optionalField`, `intField`, `posetInputFromFields`, `errorJson` | `_labels`, `_pairs_json`, `_steps_json`, ... helpers that return lists/dicts instead of writing JSON text |
| json_writer.cpp [Shivakiran] | `JsonWriter` | **dropped**: Flask's `jsonify` builds the JSON |
| http_request.cpp [Shivakiran] | `percentDecode`, `parseForm` | **kept** as `server.percent_decode` and `server.parse_form`. Werkzeug silently accepts bad escapes like `%ZZ`, but the C++ answers `400 "Bad percent-encoding in the request."`, so we decode the raw body and query string ourselves to keep that behaviour. |
| | `parseRequestHead`, `contentLength`, `statusText`, `buildResponseText`, `HttpError` | **dropped**: Flask/Werkzeug parses requests; the 1 MB limit uses `MAX_CONTENT_LENGTH` |
| http_server.cpp [Shivakiran] | sockets, `select` loop, `serveStatic`, `contentTypeFor`, `htmlEscape`, `textResponse` | **dropped**: Flask serves `frontend/` (it refuses `..` paths itself). We keep the HTML 404 page text and the `Cache-Control: no-store` header. |
| main.cpp [Shivakiran] | `readOptions`, `main` | `run.py` with `argparse`: `--port` (default 8080), `--no-browser`; binds `127.0.0.1`; opens the browser with `webbrowser` once the server starts |

## tests/

| C++ | Python |
|---|---|
| `mini_test.hpp`, `run_tests.cpp`, `test_helpers.hpp` | pytest + `tests/conftest.py` (shared helpers `pairs_poset`, `rule_poset`, `labels_text`, `pairs_text`, `build_error_field`, ...) |
| `test_util.cpp` (5), `test_parsers.cpp` (10), `test_relations.cpp` (8), `test_poset.cpp` (11), `test_hasse.cpp` (6), `test_lattice.cpp` (6), `test_game.cpp` (19), `test_data_driven.cpp` (2) = **67 tests** | `test_util.py`, `test_parsers.py`, `test_relations.py`, `test_poset.py`, `test_hasse.py`, `test_lattice.py`, `test_game.py`, `test_data_driven.py`, one Python test per C++ `TEST` with the same name, plus `test_api.py` (every route and error case through `app.test_client()`) |
