"""Start HasseQuest.

Usage:  python run.py [--port 8080] [--no-browser]

Loads the campaign levels, then serves the app on http://localhost:8080
(bound to 127.0.0.1 only, so other computers cannot connect).
"""

import argparse
import sys
import threading
import webbrowser


def read_options():
    parser = argparse.ArgumentParser(description="Run the HasseQuest server.")
    parser.add_argument("--port", type=int, default=8080, help="port to listen on (default 8080)")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    options = parser.parse_args()
    if options.port < 1 or options.port > 65535:
        parser.error("the port must be between 1 and 65535")
    return options


def main():
    options = read_options()
    try:
        from app.server import app, session      # loading the server also loads and checks the levels
    except Exception as error:
        print("Could not load levels: " + str(error))
        return 1
    url = "http://localhost:" + str(options.port)
    print("Loaded " + str(len(session.levels)) + " campaign levels.")
    print("HasseQuest running at " + url)
    print("Press Ctrl+C to stop.")
    if not options.no_browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()   # give the server a second to start
    try:
        app.run(host="127.0.0.1", port=options.port, debug=False)
    except OSError:
        print("Could not listen on port " + str(options.port) + " (is it busy?). Try: python run.py --port " +
              str(options.port + 1))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
