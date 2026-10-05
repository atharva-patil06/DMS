"""Compare two HasseQuest servers, request by request.

This was used during the migration to check the Python server against the
old C++ server (results in docs/PARITY_REPORT.md; the C++ code has since been
removed and is still in the git history). It can compare any two running
servers, e.g. before and after a change:
    python run.py --port 8080 --no-browser
    python run.py --port 8081 --no-browser      (from another copy of the project)
    python tools/parity_check.py http://127.0.0.1:8080 http://127.0.0.1:8081

It sends the same requests (every route, every test-data poset, error cases
and a whole campaign session) to both and reports every difference in the
JSON replies (key order and whitespace are ignored). Replies that are random
by design (random posets, the boss poset) are compared by their keys only.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def send(base, method, path, fields=None):
    """Send one request; return (status, parsed JSON or raw text)."""
    data = None
    url = base + path
    if method == "POST":
        data = urllib.parse.urlencode(fields or {}).encode("ascii")
    elif fields:
        url += "?" + urllib.parse.urlencode(fields)
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status, body = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    try:
        return status, json.loads(body.decode("utf-8"))
    except ValueError:
        return status, body.decode("utf-8", errors="replace")


def read_blocks(file_name):
    """The key: value blocks of a tests/data file."""
    blocks, current = [], {}
    with open(os.path.join(ROOT, "tests", "data", file_name), encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line == "":
                if current:
                    blocks.append(current)
                current = {}
            elif not line.startswith("#") and ":" in line:
                key, value = line.split(":", 1)
                current[key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


def poset_fields(block):
    fields = {"elements": block.get("elements", ""), "auto_reflexive": "1" if block.get("auto_reflexive") == "yes" else "0"}
    if "rule" in block:
        fields.update(mode="rule", rule=block["rule"])
    elif "matrix" in block:
        fields.update(mode="matrix", matrix=block["matrix"])
    else:
        fields.update(mode="pairs", relation=block.get("relation", ""))
    return fields


def build_requests():
    """(name, method, path, fields, compare) in the order they are sent. compare is "json" or "keys"."""
    requests = []
    for block in read_blocks("posets.txt"):
        fields = poset_fields(block)
        requests.append(("analyze: " + block["name"], "POST", "/api/analyze", fields, "json"))
        first = fields["elements"].replace(",", " ").split()[:2]
        requests.append(("bounds: " + block["name"], "POST", "/api/bounds", dict(fields, subset=",".join(first)), "json"))
    for block in read_blocks("hasse_checks.txt"):
        fields = dict(poset_fields(block), edges=block.get("edges", ""))
        requests.append(("check-hasse: " + block["name"], "POST", "/api/check-hasse", fields, "json"))
    extra_analyze = [
        {"elements": "1, 2, 3, 4", "mode": "pairs", "relation": "(1,2), 2<=3; 3>4  1 ≤ 4"},
        {"elements": "1,2", "mode": "pairs", "relation": "1>2, (1,2)"},
        {"elements": "a,b", "mode": "telepathy"},
        {"elements": "a,b", "mode": "rule", "rule": "modulo"},
        {"elements": "1,2", "mode": "pairs", "relation": "(1,2"},
        {"elements": "1,2", "mode": "pairs", "relation": "(1,2,3)"},
        {"elements": "1,2", "mode": "pairs", "relation": "1>"},
        {"elements": "a ab ba", "mode": "rule", "rule": "subset"},
        {"elements": "01 1", "mode": "rule", "rule": "leq"},
        {"elements": "a b c", "mode": "matrix", "matrix": "110;012;001"},
        {"elements": "a b c", "mode": "matrix", "matrix": "11;01"},
        {"mode": "pairs"},
        {"elements": "1,2", "mode": "pairs"},
    ]
    for i, fields in enumerate(extra_analyze):
        requests.append(("analyze extra " + str(i + 1), "POST", "/api/analyze", fields, "json"))
    requests += [
        ("bounds empty subset", "POST", "/api/bounds", {"elements": "1,2,3,6", "mode": "rule", "rule": "divisibility", "subset": ""}, "json"),
        ("bounds unknown label", "POST", "/api/bounds", {"elements": "1,2", "mode": "rule", "rule": "divisibility", "subset": "7"}, "json"),
        ("bounds missing subset", "POST", "/api/bounds", {"elements": "1,2", "mode": "rule", "rule": "divisibility"}, "json"),
        ("check-hasse missing edges", "POST", "/api/check-hasse", {"elements": "1,2", "mode": "rule", "rule": "divisibility"}, "json"),
        ("generate divisors 60", "GET", "/api/generate", {"type": "divisors", "n": "60"}, "json"),
        ("generate divisors default", "GET", "/api/generate", {"type": "divisors"}, "json"),
        ("generate divisors 720", "GET", "/api/generate", {"type": "divisors", "n": "720"}, "json"),
        ("generate divisors 0", "GET", "/api/generate", {"type": "divisors", "n": "0"}, "json"),
        ("generate powerset abc", "GET", "/api/generate", {"type": "powerset", "letters": "abc"}, "json"),
        ("generate powerset abcd", "GET", "/api/generate", {"type": "powerset", "letters": "abcd"}, "json"),
        ("generate powerset aa", "GET", "/api/generate", {"type": "powerset", "letters": "aa"}, "json"),
        ("generate bad size", "GET", "/api/generate", {"type": "random", "size": "abc"}, "json"),
        ("generate size 13", "GET", "/api/generate", {"type": "leq", "size": "13"}, "json"),
        ("generate unknown type", "GET", "/api/generate", {"type": "magic"}, "json"),
        ("generate missing type", "GET", "/api/generate", {}, "json"),
        ("unknown route", "GET", "/api/nothing", {}, "json"),
        ("wrong method", "GET", "/api/analyze", {}, "json"),
        ("POST level list", "POST", "/api/levels", {}, "json"),
    ]
    for poset_type in ["divisibility", "subset", "leq", "random"]:
        requests.append(("generate " + poset_type, "GET", "/api/generate", {"type": poset_type, "size": "7"}, "keys"))
    requests += campaign_requests()
    return requests


def campaign_requests():
    """A whole session: locks, wrong and right answers, hints, unlocks, scores."""
    r = [("reset", "POST", "/api/reset", {}, "json"),
         ("levels at start", "GET", "/api/levels", {}, "json"),
         ("locked level 2", "GET", "/api/levels/2", {}, "json"),
         ("no level 99", "GET", "/api/levels/99", {}, "json"),
         ("no level abc", "GET", "/api/levels/abc", {}, "json"),
         ("unknown action", "POST", "/api/levels/1/xyz", {}, "json"),
         ("GET check", "GET", "/api/levels/1/check", {}, "json"),
         ("level 1 details", "GET", "/api/levels/1", {}, "json"),
         ("level 1 bad answer", "POST", "/api/levels/1/check", {"answer": "1>99"}, "json"),
         ("level 1 missing answer", "POST", "/api/levels/1/check", {}, "json"),
         ("level 1 wrong", "POST", "/api/levels/1/check", {"answer": "1>2;1>3;2>4;2>6;3>6;4>12;6>12;1>12"}, "json"),
         ("level 1 hint 1", "POST", "/api/levels/1/hint", {}, "json"),
         ("level 1 hint 2", "POST", "/api/levels/1/hint", {}, "json"),
         ("level 1 hint 3", "POST", "/api/levels/1/hint", {}, "json"),
         ("level 1 right", "POST", "/api/levels/1/check", {"answer": "1>2;1>3;2>4;2>6;3>6;4>12;6>12"}, "json"),
         ("levels after 1", "GET", "/api/levels", {}, "json"),
         ("unlock all", "POST", "/api/unlock-all", {}, "json")]
    for level_id in range(1, 13):
        r.append(("level " + str(level_id) + " details", "GET", "/api/levels/" + str(level_id), {}, "json"))
        r.append(("level " + str(level_id) + " hint", "POST", "/api/levels/" + str(level_id) + "/hint", {}, "json"))
    answers = [
        (2, "e>a;e>b;e>c;a>ab;a>ac;b>ab;b>bc;c>ac;c>bc;ab>abc;ac>abc;bc>abc"),
        (3, "2>4;2>6;3>6;4>8;4>12;6>12;8>24;12>24;2>8"),
        (4, "minimal:2,3;maximal:12,18;least:none;greatest:none"),
        (4, "minimal:2,4;maximal:18;least:2;greatest:18"),
        (5, "minimal:e;maximal:ab,ac;least:e;greatest:none"),
        (6, "upper:12,36;lower:1,2;lub:12;glb:2"),
        (6, "upper:12,36,18;lower:1,3;lub:36;glb:none"),
        (7, "upper:c,d,t;lower:none;lub:none;glb:none"),
        (7, "upper:c,d;lower:a;lub:t;glb:a"),
        (8, "1>1;2>2;3>3;4>4;1>2;2>3;3>4;1>3;1>4;2>4"),
        (8, "1>1;1>2;3>4;4>1"),
        (9, "a>a;b>b;c>c;d>d;a>b;b>d;a>c;c>d;a>d"),
        (10, "lattice:yes"),
        (10, "lattice:no;pair:2,3"),
        (11, "lattice:no;pair:a,b"),
        (11, "lattice:no;pair:b,c"),
        (11, "lattice:no"),
        (11, "lattice:maybe"),
        (12, "lattice:no;pair:2,3"),
        (12, "lattice:yes"),
        (4, "minimal:2;least:2,3"),
        (4, "nonsense"),
    ]
    for level_id, answer in answers:
        r.append(("level " + str(level_id) + " answer " + answer[:30], "POST", "/api/levels/" + str(level_id) + "/check",
                  {"answer": answer}, "json"))
    r += [("boss before opening", "POST", "/api/levels/13/check", {"answer": "lattice:yes"}, "json"),
          ("boss details", "GET", "/api/levels/13", {}, "keys"),
          ("score", "GET", "/api/score", {}, "json"),
          ("levels at end", "GET", "/api/levels", {}, "json")]
    return r


def key_shape(value):
    """The keys of a reply (recursively), ignoring values: used for random replies."""
    if isinstance(value, dict):
        return {key: key_shape(item) for key, item in value.items() if key not in ("steps",)}
    return type(value).__name__


def compare(name, compare_mode, cpp, py):
    """Return a list of difference messages for one request."""
    (cpp_status, cpp_body), (py_status, py_body) = cpp, py
    problems = []
    if cpp_status != py_status:
        problems.append("status " + str(cpp_status) + " (C++) vs " + str(py_status) + " (Python)")
    if compare_mode == "keys":
        if key_shape(cpp_body) != key_shape(py_body):
            problems.append("keys differ")
    elif cpp_body != py_body:
        problems.append("JSON differs:\n      C++:    " + json.dumps(cpp_body)[:400] +
                        "\n      Python: " + json.dumps(py_body)[:400])
    return problems


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    cpp_base, py_base = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
    requests = build_requests()
    differences = 0
    for name, method, path, fields, compare_mode in requests:
        cpp = send(cpp_base, method, path, fields)
        py = send(py_base, method, path, fields)
        problems = compare(name, compare_mode, cpp, py)
        if problems:
            differences += 1
            print("DIFF  " + method + " " + path + "  [" + name + "]")
            for problem in problems:
                print("      " + problem)
    print()
    print(str(len(requests)) + " requests compared, " + str(differences) + " with differences.")
    return 0 if differences == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
