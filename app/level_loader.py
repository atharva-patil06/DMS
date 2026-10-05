"""Reads campaign levels from plain "key: value" text files in data/levels/.

Levels are separated by blank lines; lines starting with '#' are comments.
data/levels/index.txt lists the level files to read, one per line.
"""

import os

from core.errors import InputError
from core.parsers import PosetInput, build_poset, parse_subset
from core.poset import is_partial_order, require_partial_order
from core.relations import compute_closures
from core.types import Poset
from core.util import parse_int, split, split_whitespace, trim

KNOWN_LEVEL_TYPES = ["build_hasse", "spot_elements", "bounds", "fix_relation", "lattice", "boss"]


class LevelFileError(Exception):
    """A level file is malformed or a level makes no sense."""


class Level:
    """One campaign level, exactly as written in the level file."""

    def __init__(self):
        self.id = 0
        self.type = ""            # build_hasse, spot_elements, bounds, fix_relation, lattice, boss
        self.title = ""
        self.description = ""     # optional task text shown to the player
        self.elements = ""        # "1 2 3 4 6 12"
        self.rule = ""            # divisibility / subset / leq   (or use pairs)
        self.pairs = ""           # "1>2 1>3 ..."
        self.subset = ""          # for bounds levels
        self.hint = ""            # optional free tip
        self.points = 0
        self.unlock_after = 0     # id of the level that must be completed first (0 = none)


def is_known_level_type(level_type):
    """True for the six known level types."""
    return level_type in KNOWN_LEVEL_TYPES


def _level_error(source, line, problem):
    return LevelFileError(source + " line " + str(line) + ": " + problem)


def _number_value(value, key, source, line):
    number = parse_int(value)
    if number is None or number < 0:
        raise _level_error(source, line, "'" + key + "' must be a non-negative whole number, got '" + value + "'.")
    return number


def _apply_key(level, key, value, source, line):
    """Store one "key: value" line into the level being read."""
    if key == "id":
        level.id = _number_value(value, key, source, line)
    elif key == "type":
        level.type = value
    elif key == "title":
        level.title = value
    elif key == "description":
        level.description = value
    elif key == "elements":
        level.elements = value
    elif key == "rule":
        level.rule = value
    elif key == "pairs":
        level.pairs = value
    elif key == "subset":
        level.subset = value
    elif key == "hint":
        level.hint = value
    elif key == "points":
        level.points = _number_value(value, key, source, line)
    elif key == "unlock_after":
        level.unlock_after = _number_value(value, key, source, line)
    else:
        raise _level_error(source, line, "unknown key '" + key + "'.")


def _check_required_keys(level, source, line):
    """Check the keys every level needs once a level block has ended."""
    if level.id <= 0:
        raise _level_error(source, line, "level is missing a positive 'id'.")
    if not is_known_level_type(level.type):
        raise _level_error(source, line, "unknown level type '" + level.type + "'.")
    if level.title == "":
        raise _level_error(source, line, "level " + str(level.id) + " has no 'title'.")
    if level.points <= 0:
        raise _level_error(source, line, "level " + str(level.id) + " needs 'points' > 0.")
    has_relation = level.rule != "" or level.pairs != ""
    if level.type != "boss" and (level.elements == "" or not has_relation):
        raise _level_error(source, line, "level " + str(level.id) + " needs 'elements' and either 'rule' or 'pairs'.")


def parse_levels(text, source_name):
    """Parse all levels in one text. Raises LevelFileError("<source> line N: <problem>")."""
    levels = []
    lines = split(text + "\n", "\n")
    current = Level()
    in_level = False
    for i in range(len(lines)):
        line = lines[i]
        if line == "" or line[0] == "#":          # blank line ends a level; '#' = comment
            if in_level and line == "":
                _check_required_keys(current, source_name, i)
                levels.append(current)
                current = Level()
                in_level = False
            continue
        colon = line.find(":")
        if colon < 0:
            raise _level_error(source_name, i + 1, "expected 'key: value' but found '" + line + "'.")
        _apply_key(current, trim(line[:colon]), trim(line[colon + 1:]), source_name, i + 1)
        in_level = True
    return levels


def level_input(level):
    """The core input for a level's poset.

    Reflexive pairs are added automatically except in fix_relation levels,
    where a missing (a,a) is part of the puzzle.
    """
    if level.rule != "":
        return PosetInput(elements=level.elements, mode="rule", rule=level.rule,
                          auto_reflexive=level.type != "fix_relation")
    return PosetInput(elements=level.elements, mode="pairs", relation=level.pairs,
                      auto_reflexive=level.type != "fix_relation")


def _validate_fix_level(poset, name):
    """A fix_relation level must fail an axiom, and R* must be a poset.

    Then the unique best answer is R*, the reflexive-transitive closure.
    """
    if is_partial_order(poset).is_poset:
        raise LevelFileError(name + ": a fix_relation level must not already be a partial order.")
    fixed = Poset(poset.labels, compute_closures(poset).reflexive_transitive)
    if not is_partial_order(fixed).is_poset:
        raise LevelFileError(name + ": this relation cannot be fixed by adding pairs (it has a cycle).")


def validate_level(level):
    """Check the level makes sense mathematically. Raises LevelFileError naming the level."""
    if level.type == "boss":
        return              # boss posets are generated at play time
    name = "Level " + str(level.id) + " (" + level.title + ")"
    try:
        poset = build_poset(level_input(level)).poset
        if level.type == "fix_relation":
            _validate_fix_level(poset, name)
            return
        require_partial_order(poset, "this level")
        if level.type == "bounds":
            if level.subset == "":
                raise LevelFileError(name + ": a bounds level needs a 'subset'.")
            parse_subset(level.subset, poset.labels, "subset")
    except InputError as error:
        raise LevelFileError(name + ": " + error.message)


def _read_whole_file(path):
    try:
        with open(path, "rb") as handle:
            return handle.read().decode("utf-8")
    except OSError:
        raise LevelFileError("Cannot open " + path + ". Run python run.py from the project folder.")


def _check_unique_ids(levels):
    """Two levels with the same id would make the campaign ambiguous."""
    for i in range(len(levels)):
        for j in range(i):
            if levels[i].id == levels[j].id:
                raise LevelFileError("Two levels use id " + str(levels[i].id) + ".")


def load_levels(level_dir):
    """Read <level_dir>/index.txt and every file it lists; validate every level."""
    file_names = split_whitespace(_read_whole_file(os.path.join(level_dir, "index.txt")))
    all_levels = []
    for file_name in file_names:
        for level in parse_levels(_read_whole_file(os.path.join(level_dir, file_name)), file_name):
            validate_level(level)
            all_levels.append(level)
    _check_unique_ids(all_levels)
    if len(all_levels) == 0:
        raise LevelFileError("No levels found in " + level_dir + ".")
    return all_levels
