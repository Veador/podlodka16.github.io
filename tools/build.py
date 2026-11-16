#!/usr/bin/env python3
"""Build the Terminal deck from private/talk-draft.html (the source with speaker notes).

The source deck is read only. Result = source + embedded fonts + shared token
layer + theme CSS + theme JS, written to ../build/talk-terminal.html (that
file keeps the notes bar; it is git-ignored). Re-run after editing the source:

    python3 tools/build.py
"""
from html import escape
from pathlib import Path
import base64
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "private" / "talk-draft.html"
THEMES = {
    # auto_first: slides where terminal.js reveals the first build group itself
    # (keep in sync with AUTO_FIRST_BUILD there); group19: one click for all
    # "Добавилось" blocks on slide 19, appearing one after another.
    "terminal":  {"label": "Terminal",  "fonts": ["JetBrainsMono", "IBMPlexSans"], "js": True,
                  "auto_first": ["slide-03", "slide-13", "slide-14", "slide-18"], "group19": True, "morpheus": True, "quotes": True, "portraits": True},
}


def slide_span(html: str, slide_id: str) -> tuple[int, int]:
    m = re.search(rf'<section data-notes-id="{slide_id}".*?</section>', html, re.S)
    assert m, f"{slide_id} not found"
    return m.start(), m.end()


def set_clicks(html: str, slide_id: str, change) -> str:
    """Rewrite the '[Кликов на слайде: N]' note line of one slide."""
    a, b = slide_span(html, slide_id)
    sec, n = re.subn(r"\[Кликов на слайде: (\d+)\]", lambda m: f"[Кликов на слайде: {change(int(m.group(1)))}]", html[a:b], count=1)
    assert n == 1, f"no click counter on {slide_id}"
    return html[:a] + sec + html[b:]


def group_slide19(html: str) -> str:
    a, b = slide_span(html, "slide-19")
    k = 0

    def node(_m: re.Match) -> str:
        nonlocal k
        out = f'<div class="node mine build slow" data-b="1" style="--d:{k * 0.25:.2f}s">'
        k += 1
        return out
    sec = re.sub(r'<div class="node mine build">', node, html[a:b])
    assert k >= 1, "slide-19: no added blocks found"
    sec, n = re.subn(r'<div class="callout build"', '<div class="callout build slow" data-b="1"', sec, count=1)
    assert n == 1, "slide-19: callout not found"
    sec = sec.replace('data-b="1" style="font-size:34px"', f'data-b="1" style="font-size:34px;--d:{k * 0.25:.2f}s"', 1)
    html = html[:a] + sec + html[b:]
    return set_clicks(html, "slide-19", lambda _: 1)


def img_uri(name: str) -> str:
    mime = "image/svg+xml" if name.endswith(".svg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode((HERE / "src" / "img" / name).read_bytes()).decode()


def morpheus_slide10(html: str) -> str:
    """Slide 10: Morpheus peeks over the black box (head only, cut just below
    the eyes); the arrows become his palms: red pill left ("Разобраться", the truth),
    blue pill right. Pieces are flat SVGs drawn by src/img/make_svg.py."""
    a, b = slide_span(html, "slide-10")
    sec = html[a:b]
    swaps = [
        ('<div class="flow" style="align-items:center">',
         '<div class="flow" style="align-items:center;margin-top:110px">'),
        ('<div class="arr build" data-b="2" style="width:80px">←</div>',
         f'<div class="hand l build" data-b="2"><img src="{img_uri("morpheus-hand-red.svg")}" alt="Ладонь с красной пилюлей"></div>'),
        ('<div class="box">?</div>',
         f'<div class="bbox"><img class="peek" src="{img_uri("morpheus-head.svg")}" alt="Морфеус выглядывает из-за ящика"><div class="box">?</div></div>'),
        ('<div class="arr build" data-b="1" style="width:80px">→</div>',
         f'<div class="hand r build" data-b="1"><img src="{img_uri("morpheus-hand-blue.svg")}" alt="Ладонь с синей пилюлей"></div>'),
    ]
    for old, new in swaps:
        assert sec.count(old) == 1, f"slide-10: expected one {old!r}"
        sec = sec.replace(old, new)
    return html[:a] + sec + html[b:]


# Hard-coded SVG colours in the source -> theme tokens. Rewritten as inline
# style (var() is not allowed in presentation attributes, and document CSS does
# not reach the <use> clones of <symbol> content; inherited custom properties do).
SVG_TOKENS = {
    "#2b5ba8": "--accent", "#5a6270": "--muted", "#b4440e": "--bad", "#1a1a1a": "--ink",
    "#eef3fb": "--minebg", "#f0f1f3": "--softbg", "#fff": "--face",
}
SVG_TAG = re.compile(r"<(?:path|circle|rect|ellipse|g|text|line|polygon|polyline)\b[^>]*>")
SVG_ATTR = re.compile(r'\s(fill|stroke)="(#[0-9a-fA-F]{3,6})"')


def tokenize_svg(html: str) -> str:
    def fix(tag: re.Match) -> str:
        t = tag.group(0)
        decls = [f"{p}:var({SVG_TOKENS[c.lower()]})" for p, c in SVG_ATTR.findall(t) if c.lower() in SVG_TOKENS]
        if not decls:
            return t
        t = SVG_ATTR.sub(lambda m: "" if m.group(2).lower() in SVG_TOKENS else m.group(0), t)
        style = ";".join(decls)
        if ' style="' in t:
            return t.replace(' style="', f' style="{style};', 1)
        return t[:-2] + f' style="{style}"/>' if t.endswith("/>") else t[:-1] + f' style="{style}">'
    return SVG_TAG.sub(fix, html)


# Robot head: in the source the antenna ball (top y=82) pokes out of the
# background circle (top y=85). Shrink everything above the circle to 86%
# and lower it, so the antenna top lands at y~124.
BOT_HEAD = 'transform="translate(270 290) scale(.86) translate(-270 -275)"'


def fit_bot_head(html: str) -> str:
    m = re.search(r'(<symbol id="bot"[^>]*>\s*<circle\b[^>]*/>)(.*?)(</symbol>)', html, re.S)
    assert m, "bot symbol not found"
    return html[:m.start()] + f'{m.group(1)}\n    <g {BOT_HEAD}>{m.group(2)}</g>\n  {m.group(3)}' + html[m.end():]


def portraits_slides_2_4(html: str) -> str:
    """Terminal: replace the robot / human icons on slides 2 and 4 with the
    two-tone stencil portraits of Agent Smith (AI agent, also the swapped
    'AI client') and Neo (client). The SVGs in src/img/ draw only in
    currentColor; the colour comes from CSS (see terminal.css), the dark disc
    is drawn here and the bust is clipped to it."""
    def inner(name: str) -> str:
        s = (HERE / "src" / "img" / f"{name}.svg").read_text(encoding="utf-8")
        s = re.sub(r"<title>.*?</title>", "", s, flags=re.S)
        return s[s.index(">") + 1:s.rindex("</svg>")]

    symbols = ('\n  <clipPath id="portrait-clip"><circle cx="210" cy="210" r="190"/></clipPath>'
               + "".join(
                   f'\n  <symbol id="{n}" viewBox="0 0 420 420"><circle cx="210" cy="210" r="190" style="fill:var(--card)"/>'
                   f'<g clip-path="url(#portrait-clip)">{inner(n)}</g></symbol>'
                   for n in ("smith", "neo")) + "\n")
    anchor = html.index('<symbol id="human"')
    end = html.index("</svg>", anchor)
    html = html[:end] + symbols + html[end:]
    for slide_id, swaps in (("slide-02", (('href="#bot"', 'href="#smith"'), ('href="#human"', 'href="#neo"'))),
                            ("slide-04", (('href="#bot"', 'href="#smith"'),))):
        a, b = slide_span(html, slide_id)
        sec = html[a:b]
        for old, new in swaps:
            assert old in sec, f"{slide_id}: {old} not found"
            sec = sec.replace(old, new)
        html = html[:a] + sec + html[b:]
    return html


def add_quotes(html: str) -> str:
    """Add the original footer quote to each slide listed in src/quotes.json."""
    quotes = json.loads((HERE / "src" / "quotes.json").read_text(encoding="utf-8"))
    for slide_id, text in quotes.items():
        a, b = slide_span(html, slide_id)
        sec = html[a:b]
        end = sec.rindex("</section>")
        sec = sec[:end] + f'<div class="quote">{escape(text, quote=False)}</div>\n' + sec[end:]
        html = html[:a] + sec + html[b:]
    return html


def read(name: str) -> str:
    return (HERE / "src" / name).read_text(encoding="utf-8")


def build(theme: str, cfg: dict, html: str) -> str:
    slides = len(re.findall(r"<section\b", html))
    fonts = "\n".join(read(f"fonts/{f}.css") for f in cfg["fonts"])
    css = read("shared.css") + "\n" + read(f"{theme}.css").replace("/22]", f"/{slides}]")
    head = (f'<style id="theme-fonts">\n{fonts}</style>\n'
            f'<style id="theme" data-theme="{theme}">\n{css}</style>\n</head>')
    if cfg.get("group19"):
        html = group_slide19(html)
    if cfg.get("morpheus"):
        html = morpheus_slide10(html)
    if cfg.get("quotes"):
        html = add_quotes(html)
    if cfg.get("portraits"):
        html = portraits_slides_2_4(html)
    for slide_id in cfg.get("auto_first", []):
        html = set_clicks(html, slide_id, lambda n: max(n - 1, 0))
    out = html.replace("</head>", head, 1)
    out = re.sub(r"<title>(.*?)</title>", lambda m: f"<title>{m.group(1)} · {cfg['label']}</title>", out, count=1)
    out = out.replace("<body>", f'<body class="theme-{theme}">', 1)
    if cfg.get("js"):
        i = out.rindex("</body>")
        out = out[:i] + f'<script id="theme-js">\n{read(theme + ".js")}</script>\n' + out[i:]
    return out


def main() -> None:
    html = SRC.read_text(encoding="utf-8")
    for checks in ("</head>", "<body>", "</body>", "<title>"):
        assert html.count(checks) == 1, f"expected exactly one {checks} in source"
    html = tokenize_svg(fit_bot_head(html))
    left = [c for c in SVG_ATTR.findall(html) if c[1].lower() in SVG_TOKENS]
    assert not left, f"untokenized SVG colours: {left}"
    for theme, cfg in THEMES.items():
        dst = ROOT / "build" / f"talk-{theme}.html"
        dst.write_text(build(theme, cfg, html), encoding="utf-8")
        print(f"{dst.name}: {dst.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
