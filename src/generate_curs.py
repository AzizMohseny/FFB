"""
generate_curs.py

Generates the GPOS `curs` (cursive attachment) feature from Ex/_Ex anchors:
    Ex  = exit point (this glyph offers a connection forward)
    _Ex = entry point (this glyph receives a connection from the previous one)

Usage:
    python3 generate_curs.py <normalized-ufo-path> [--out curs.fea]
"""

import argparse
from pathlib import Path

from fontTools.ufoLib.glifLib import GlyphSet


class _AnchorCollector:
    def __init__(self):
        self.anchors = []

    def addAnchor(self, anchorDict):
        self.anchors.append(dict(anchorDict))

    def addComponent(self, *a, **k):
        pass

    def addPoint(self, *a, **k):
        pass

    def addImage(self, *a, **k):
        pass


def scan_curs_anchors(ufo_path: Path):
    gs = GlyphSet(str(ufo_path / "glyphs"))
    result = {}
    for glyph_name in gs.keys():
        collector = _AnchorCollector()
        gs.readGlyph(glyph_name, collector)
        entry = exit_ = None
        for a in collector.anchors:
            if a.get("name") == "Ex":
                exit_ = (a.get("x", 0), a.get("y", 0))
            elif a.get("name") == "_Ex":
                entry = (a.get("x", 0), a.get("y", 0))
        if entry or exit_:
            result[glyph_name] = (entry, exit_)
    return result


def fea_anchor(xy):
    if xy is None:
        return "<anchor NULL>"
    x, y = xy
    return f"<anchor {int(round(x))} {int(round(y))}>"


def generate_curs_feature(anchors: dict) -> str:
    lines = [
        "feature curs {",
        "  # GPOS feature: Cursive Attachment",
        "  # auto-generated from Ex/_Ex anchors -- do not hand-edit",
        "",
        "  lookup curs_auto {",
        "    lookupflag RightToLeft IgnoreMarks;",
    ]
    for glyph, (entry, exit_) in sorted(anchors.items()):
        lines.append(f"    pos cursive {glyph} {fea_anchor(entry)} {fea_anchor(exit_)};")
    lines.append("  } curs_auto;")
    lines.append("} curs;")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ufo_path")
    ap.add_argument("--out", default="generated_curs.fea")
    args = ap.parse_args()

    ufo_path = Path(args.ufo_path)
    anchors = scan_curs_anchors(ufo_path)
    fea_text = generate_curs_feature(anchors)
    Path(args.out).write_text(fea_text, encoding="utf-8")
    print(f"Found cursive anchors on {len(anchors)} glyphs.")
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
