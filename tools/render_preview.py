#!/usr/bin/env python3
"""Render preview.svg for a Terminal.app profile, using the colors stored in it.

    python3 tools/render_preview.py tahoe/Tahoe.terminal

Writes preview.svg next to the profile. Because the colors are read from the
.terminal file itself, the preview always matches what Terminal will show.
"""
import plistlib
import sys
from html import escape
from pathlib import Path

ANSI = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]

FONT = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
CHAR_W = 7.8   # approximate advance of a 13px monospace glyph
LINE_H = 20
PAD = 20
TITLE_H = 32
WIDTH = 720


def decode_color(data):
    for o in plistlib.loads(data)["$objects"]:
        if isinstance(o, dict) and ("NSRGB" in o or "NSComponents" in o):
            raw = o.get("NSRGB") or o.get("NSComponents")
            r, g, b = (float(x) for x in raw.rstrip(b"\x00").split()[:3])
            return "#%02x%02x%02x" % tuple(round(max(0, min(1, v)) * 255) for v in (r, g, b))
    raise ValueError("no RGB color in archive")


def load(path):
    p = plistlib.load(open(path, "rb"))
    c = {k: decode_color(v) for k, v in p.items() if isinstance(v, bytes) and k.endswith("Color")}
    pal = {
        "name": p.get("name", Path(path).stem),
        "bg": c["BackgroundColor"],
        "fg": c["TextColor"],
        "bold": c.get("TextBoldColor", c["TextColor"]),
        "cursor": c.get("CursorColor", c["TextColor"]),
        "sel": c.get("SelectionColor", c["TextColor"]),
    }
    for i, n in enumerate(ANSI):
        pal[i] = c[f"ANSI{n}Color"]
        pal[i + 8] = c[f"ANSIBright{n}Color"]
    return pal


def script(pal):
    """Sample session: each line is a list of (text, color, bold) spans."""
    fg, B = pal["fg"], pal["bold"]
    prompt = [("~/projects/demo", pal[4], True), (" (main)", pal[5], False), (" $ ", fg, False)]
    return [
        prompt + [("ls", fg, False)],
        [("README.md  ", fg, False), ("data/", pal[4], True), ("  ", fg, False), ("scripts/", pal[4], True),
         ("  results.csv  ", fg, False), ("run.sh", pal[2], True), ("*", fg, False)],
        prompt + [("git status -s", fg, False)],
        [(" M ", pal[1], False), ("src/model.py", fg, False)],
        [("A  ", pal[2], False), ("src/plot.py", fg, False)],
        [("?? ", pal[1], False), ("notes.txt", fg, False)],
        prompt + [("git log --oneline -2", fg, False)],
        [("3f9c2e1 ", pal[3], False), ("(", pal[3], False), ("HEAD -> ", pal[6], True), ("main", pal[2], True),
         (")", pal[3], False), (" Add plotting helpers", fg, False)],
        [("a71d04b ", pal[3], False), ("Tune model defaults", fg, False)],
        prompt + [("./run.sh --verbose", fg, False)],
        [("[info] ", pal[6], False), (" loaded 1,204 records", fg, False)],
        [("[warn] ", pal[3], False), (" 3 rows missing values", fg, False)],
        [("[error]", pal[1], True), (" could not reach server, retrying", fg, False)],
        [("[debug]", pal[8], False), (" cache hit ratio 0.93", pal[8], False)],
        [("✔ ", pal[2], True), ("done in 2.4s", B, True), ("  →  ", fg, False), ("results.csv", pal[5], False)],
        prompt + [("CURSOR", None, False)],
    ]


def render(path):
    pal = load(path)
    lines = script(pal)
    body_h = len(lines) * LINE_H
    swatch_top = TITLE_H + PAD + body_h + 18
    sw, sh, gap = 76, 30, 8
    height = swatch_top + 2 * (sh + 22) + PAD
    sel_line = 7  # highlight the HEAD commit line as a text selection

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(pal["name"])} terminal color scheme preview">',
        f'<rect width="{WIDTH}" height="{height}" rx="10" fill="{pal["bg"]}"/>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" fill="none" stroke="#000" stroke-opacity="0.25"/>',
        # title bar
        f'<path d="M10 0H{WIDTH - 10}A10 10 0 0 1 {WIDTH} 10V{TITLE_H}H0V10A10 10 0 0 1 10 0Z" fill="#000" fill-opacity="0.18"/>',
    ]
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{20 + i * 20}" cy="{TITLE_H / 2}" r="6" fill="{c}"/>')
    out.append(
        f'<text x="{WIDTH / 2}" y="{TITLE_H / 2 + 4}" text-anchor="middle" font-family="-apple-system, Helvetica, Arial, sans-serif" '
        f'font-size="12" fill="{pal["fg"]}" fill-opacity="0.75">{escape(pal["name"])} — zsh — 90×50</text>'
    )

    out.append(f'<g font-family="{FONT}" font-size="13" xml:space="preserve">')
    for n, spans in enumerate(lines):
        y = TITLE_H + PAD + n * LINE_H + 14
        if n == sel_line:
            text_len = sum(len(t) for t, _, _ in spans)
            out.append(f'<rect x="{PAD - 2}" y="{y - 14}" width="{text_len * CHAR_W + 4}" height="{LINE_H - 2}" fill="{pal["sel"]}"/>')
        # One <text> per line with colored <tspan>s, so the renderer's own font
        # metrics position each span (estimating glyph widths drifts).
        tspans = []
        for text, color, bold in spans:
            if text == "CURSOR":
                tspans.append(f'<tspan fill="{pal["cursor"]}">\u2588</tspan>')  # block cursor
                continue
            weight = ' font-weight="bold"' if bold else ""
            tspans.append(f'<tspan fill="{color}"{weight}>{escape(text)}</tspan>')
        out.append(f'<text x="{PAD}" y="{y}" style="white-space:pre">{"".join(tspans)}</text>')
    out.append("</g>")

    # palette swatches: normal colors on the first row, bright on the second
    left = (WIDTH - (8 * sw + 7 * gap)) / 2
    for row, label in ((0, "normal"), (1, "bright")):
        y = swatch_top + row * (sh + 22)
        for i in range(8):
            x = left + i * (sw + gap)
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{sw}" height="{sh}" rx="5" fill="{pal[i + 8 * row]}" '
                       f'stroke="{pal["fg"]}" stroke-opacity="0.2"/>')
            out.append(f'<text x="{x + sw / 2:.1f}" y="{y + sh + 14}" text-anchor="middle" font-family="{FONT}" '
                       f'font-size="10" fill="{pal["fg"]}" fill-opacity="0.7">{pal[i + 8 * row]}</text>')
    out.append("</svg>")

    dest = Path(path).with_name("preview.svg")
    dest.write_text("\n".join(out) + "\n")
    print(f"wrote {dest}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for arg in sys.argv[1:]:
        render(arg)
