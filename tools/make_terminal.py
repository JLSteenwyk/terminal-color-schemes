#!/usr/bin/env python3
"""Build a macOS Terminal.app profile (.terminal) from a palette.json file.

    python3 tools/make_terminal.py tahoe/palette.json

Writes <Name>.terminal next to the palette. Font and window size are taken
from the palette's "font"/"columns"/"rows" keys, defaulting to Menlo 11pt
at 90x50 to match the other profiles in this repo.
"""
import json
import plistlib
import sys
from pathlib import Path

ANSI = ["Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White"]


def archive(obj_dict, classname, classes):
    """Wrap one object in the NSKeyedArchiver structure Terminal expects."""
    obj = dict(obj_dict, **{"$class": plistlib.UID(2)})
    return plistlib.dumps(
        {
            "$version": 100000,
            "$archiver": "NSKeyedArchiver",
            "$top": {"root": plistlib.UID(1)},
            "$objects": ["$null", obj, {"$classname": classname, "$classes": classes}],
        },
        fmt=plistlib.FMT_BINARY,
    )


def color(hex_value):
    h = hex_value.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    rgb = f"{r:.10g} {g:.10g} {b:.10g}".encode() + b"\x00"
    # NSColorSpace 2 = device RGB, as in profiles exported by Terminal.
    return archive({"NSRGB": rgb, "NSColorSpace": 2}, "NSColor", ["NSColor", "NSObject"])


def font(name, size):
    data = plistlib.dumps(
        {
            "$version": 100000,
            "$archiver": "NSKeyedArchiver",
            "$top": {"root": plistlib.UID(1)},
            "$objects": [
                "$null",
                {"NSName": plistlib.UID(2), "NSSize": float(size), "NSfFlags": 16, "$class": plistlib.UID(3)},
                name,
                {"$classname": "NSFont", "$classes": ["NSFont", "NSObject"]},
            ],
        },
        fmt=plistlib.FMT_BINARY,
    )
    return data


def build(palette_path):
    palette_path = Path(palette_path)
    p = json.loads(palette_path.read_text())
    profile = {
        "name": p["name"],
        "type": "Window Settings",
        "ProfileCurrentVersion": 2.09,
        "columnCount": p.get("columns", 90),
        "rowCount": p.get("rows", 50),
        "Font": font(p.get("font", "Menlo-Regular"), p.get("font_size", 11)),
        "BackgroundColor": color(p["background"]),
        "TextColor": color(p["text"]),
        "TextBoldColor": color(p["bold"]),
        "CursorColor": color(p["cursor"]),
        "SelectionColor": color(p["selection"]),
    }
    for i, name in enumerate(ANSI):
        profile[f"ANSI{name}Color"] = color(p["normal"][i])
        profile[f"ANSIBright{name}Color"] = color(p["bright"][i])
    out = palette_path.with_name(f"{p['name']}.terminal")
    with open(out, "wb") as f:
        plistlib.dump(profile, f, fmt=plistlib.FMT_XML)
    print(f"wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for arg in sys.argv[1:]:
        build(arg)
