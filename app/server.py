"""The Flask app object: static files, form decoding and error handlers.

Flask replaces the hand-written socket server. It serves frontend/ (and
refuses ".." paths itself), and every /api/ error comes back as JSON
{"ok": false, "error": ..., "field": ...}, so a bad request never crashes the
server or shows an HTML error page to the frontend.
"""

import os

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from app.game import GameSession
from app.level_loader import load_levels
from core.errors import InputError

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
LEVELS_DIR = os.path.join(ROOT_DIR, "data", "levels")
MAX_BODY_BYTES = 1024 * 1024        # 1 MB request body limit

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES
app.json.sort_keys = False           # keep keys in the order we write them
app.json.ensure_ascii = False

# The single player's session: the only mutable state in the program.
session = GameSession(load_levels(LEVELS_DIR))


class RequestError(Exception):
    """A malformed request (e.g. bad percent-encoding), with the HTTP status to reply with."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------- form decoding ----------

def _hex_value(char):
    if "0" <= char <= "9":
        return ord(char) - ord("0")
    if "a" <= char <= "f":
        return ord(char) - ord("a") + 10
    if "A" <= char <= "F":
        return ord(char) - ord("A") + 10
    return -1


def percent_decode(text):
    """Decode %XX escapes and '+' (space). Raises RequestError 400 on a bad escape."""
    decoded = bytearray()
    i = 0
    while i < len(text):
        char = text[i]
        if char == "+":
            decoded += b" "
        elif char == "%":
            if i + 2 >= len(text) or _hex_value(text[i + 1]) < 0 or _hex_value(text[i + 2]) < 0:
                raise RequestError(400, "Bad percent-encoding in the request.")
            decoded.append(_hex_value(text[i + 1]) * 16 + _hex_value(text[i + 2]))
            i += 2
        else:
            decoded += char.encode("utf-8")
        i += 1
    return decoded.decode("utf-8", errors="replace")


def parse_form(text):
    """Parse "a=1&b=two" into a dict, percent-decoding names and values."""
    fields = {}
    for item in text.split("&"):
        item = item.strip(" \t\r\n")
        if item == "":
            continue
        eq = item.find("=")
        name = item if eq < 0 else item[:eq]
        value = "" if eq < 0 else item[eq + 1:]
        fields[percent_decode(name)] = percent_decode(value)
    return fields


def body_fields():
    """The form fields of a POST body (Flask enforces the 1 MB limit here)."""
    return parse_form(request.get_data().decode("latin-1"))


def query_fields():
    """The form fields of the query string (?type=leq&size=3)."""
    return parse_form(request.query_string.decode("latin-1"))


# ---------- replies ----------

def error_reply(status, message, field):
    """The JSON error reply used everywhere: {"ok": false, "error": ..., "field": ...}."""
    return jsonify({"ok": False, "error": message, "field": field}), status


def _html_page(status, title, message):
    page = ("<!doctype html><html><body style=\"font-family:sans-serif\"><h1>" + str(status) + " " + title +
            "</h1><p>" + _html_escape(message) + "</p><p><a href=\"/\">Back to HasseQuest</a></p></body></html>")
    return page, status, {"Content-Type": "text/html; charset=utf-8"}


def _html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _is_api_request():
    return request.path.startswith("/api/")


@app.route("/")
def index_page():
    """'/' serves the single-page frontend."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.after_request
def no_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(InputError)
def handle_input_error(error):
    """Bad user input found by the math core -> 400 with the field at fault."""
    return error_reply(400, error.message, error.field)


@app.errorhandler(RequestError)
def handle_request_error(error):
    return error_reply(error.status, error.message, "request")


@app.errorhandler(404)
def handle_not_found(error):
    if _is_api_request():
        return error_reply(404, "Unknown API route " + request.method + " " + request.path + ".", "path")
    return _html_page(404, "Not Found", "The page " + request.path + " does not exist.")


@app.errorhandler(405)
def handle_wrong_method(error):
    """A known path with the wrong method counts as an unknown route (as before);
    methods other than GET/POST are refused."""
    if request.method not in ("GET", "POST"):
        return error_reply(405, "Only GET and POST are supported.", "request")
    if _is_api_request():
        return error_reply(404, "Unknown API route " + request.method + " " + request.path + ".", "path")
    return _html_page(405, "Method Not Allowed", "Static files only support GET.")


@app.errorhandler(413)
def handle_too_large(error):
    return error_reply(413, "Request body is too large (limit 1 MB).", "request")


@app.errorhandler(Exception)
def handle_unexpected(error):
    """Anything else: never crash, never show a raw error."""
    if isinstance(error, HTTPException):
        return error_reply(error.code, error.description, "request")
    return error_reply(500, "The server could not process this request.", "request")


# Registers the /api/... routes on `app` (api.py imports `app` from this file).
from app import api  # noqa: E402,F401
