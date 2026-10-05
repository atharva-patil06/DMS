# build_report.py - turns report.md into report.html (10pt, small margins).
# Then print report.html to report.pdf with any browser, e.g.:
#   msedge --headless --print-to-pdf=report.pdf report.html
# Uses the Python "markdown" package (pip install markdown).
import pathlib

import markdown

HERE = pathlib.Path(__file__).parent
CSS = """
@page { size: A4; margin: 9mm 11mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.25; color: #111; margin: 0; }
h1 { font-size: 14pt; margin: 0 0 3pt; color: #312e81; }
h2 { font-size: 10.6pt; margin: 6pt 0 2pt; color: #312e81; border-bottom: 1px solid #c7c9e6; }
p { margin: 2pt 0; text-align: justify; }
ul { margin: 2pt 0; padding-left: 14pt; }
li { margin: 1pt 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 2pt 0; }
th, td { border: 1px solid #c9cbd6; padding: 1.5pt 5pt; text-align: left; }
th { background: #eef0fa; }
code { font-family: Consolas, monospace; font-size: 8.8pt; }
img.arch { display: block; width: 78%; margin: 2pt auto; }
.shots { display: flex; gap: 6pt; margin: 2pt 0; }
.shots img { width: 50%; border: 1px solid #ccc; }
"""

body = markdown.markdown((HERE / "report.md").read_text(encoding="utf-8"), extensions=["tables"])
html = ("<!doctype html><html><head><meta charset='utf-8'><title>HasseQuest report</title><style>"
        + CSS + "</style></head><body>" + body + "</body></html>")
(HERE / "report.html").write_text(html, encoding="utf-8")
print("wrote report.html")
