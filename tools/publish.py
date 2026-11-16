#!/usr/bin/env python3
"""Public page for GitHub Pages: ../build/talk-terminal.html -> ../index.html.

Presenter tools are removed from what visitors get: the bottom bar (timer,
plan, notes toggle, "download HTML") is hidden for good, the N shortcut no
longer opens the notes panel, and the speaker notes / plan text are stripped
from the page source. Keyboard navigation (← → space, F) stays.

    python3 tools/build.py && python3 tools/publish.py   # then commit and push index.html
"""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "build" / "talk-terminal.html"
DST = ROOT / "index.html"

# The deck script looks the bar elements up by id, so they stay in the DOM but never render.
HIDE = '<style id="public-hide">#bar,#notes{display:none !important}</style>\n</head>'
NOTES_KEY = "else if(e.key==='n'||e.key==='N'||e.key==='т'||e.key==='Т'){document.body.classList.toggle('shownotes');fit();}\n  "


def main() -> None:
    html = SRC.read_text(encoding="utf-8")
    assert html.count("</head>") == 1, "expected one </head>"
    assert html.count(NOTES_KEY) == 1, "notes shortcut not found: deck script changed?"
    html = html.replace(NOTES_KEY, "", 1).replace("</head>", HIDE, 1)
    html, notes = re.subn(r'\sdata-notes="[^"]*"', "", html)
    html, plans = re.subn(r'\sdata-plan="[^"]*"', "", html)
    assert notes == plans == len(re.findall(r"<section\b", html)), (notes, plans)
    DST.write_text(html, encoding="utf-8")
    print(f"{DST.name}: {DST.stat().st_size // 1024} KB, stripped notes on {notes} slides")


if __name__ == "__main__":
    main()
