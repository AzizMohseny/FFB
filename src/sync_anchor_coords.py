"""
sync_anchor_coords.py

The first, minimal piece of the "builder": given (1) a UFO whose glyph
anchors may have been moved/tuned in the font editor, and (2) an EXISTING
GPOS fea file (mark/mkmk) whose structure (which marks belong to which
class, which bases attach where) is already correct, this updates ONLY
the numeric <anchor X Y> coordinates in that fea file to match the
CURRENT anchor positions in the UFO -- leaving every class name, glyph
membership, and line structure untouched.

This intentionally does NOT touch GSUB tables and does NOT regenerate
structure from scratch -- only numbers are swapped in place, per the
designer's instruction to go step by step.

How it matches a fea line to a UFO anchor:
    markClass <glyph> <anchor X Y> @<SLOT>;      -> glyph's "_<SLOT>" anchor (mark side)
    pos base  <glyph> <anchor X Y> mark @<SLOT>  -> glyph's "<SLOT>" anchor (base side)
    pos mark  <glyph> <anchor X Y> mark @<SLOT>  -> glyph's "<SLOT>" anchor (base side, mkmk host)

Usage:
    python3 sync_anchor_coords.py <ufo_path> <fea_path> [--out synced.fea]
"""

import argparse
import re
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


def load_ufo_anchors(ufo_path: Path):
    """Returns {(glyph_name, anchor_name): (x, y)} for every anchor in the UFO."""
    gs = GlyphSet(str(ufo_path / "glyphs"))
    result = {}
    for glyph_name in gs.keys():
        collector = _AnchorCollector()
        gs.readGlyph(glyph_name, collector)
        for a in collector.anchors:
            name = a.get("name")
            if name:
                result[(glyph_name, name)] = (a.get("x", 0), a.get("y", 0))
    return result


# Matches: markClass <glyph> <anchor X Y> @<slot>;
MARKCLASS_RE = re.compile(
    r'(markClass\s+(\S+)\s+<anchor\s+)(-?\d+)\s+(-?\d+)(>\s*@(\w+)\s*;)'
)
# Matches: pos base <glyph> <anchor X Y> mark @<slot>   OR   pos mark <glyph> <anchor X Y> mark @<slot>
POSBASE_RE = re.compile(
    r'(pos\s+(?:base|mark)\s+(\S+)\s+<anchor\s+)(-?\d+)\s+(-?\d+)(>\s*mark\s*@(\w+))'
)


def sync_fea_text(fea_text: str, ufo_anchors: dict):
    updated_count = 0
    missing = []

    def repl_markclass(m):
        nonlocal updated_count
        prefix, glyph, old_x, old_y, suffix, slot = m.groups()
        key = (glyph, f"_{slot}")
        if key not in ufo_anchors:
            missing.append(key)
            return m.group(0)
        x, y = ufo_anchors[key]
        updated_count += 1
        return f"{prefix}{int(round(x))} {int(round(y))}{suffix}"

    def repl_posbase(m):
        nonlocal updated_count
        prefix, glyph, old_x, old_y, suffix, slot = m.groups()
        key = (glyph, slot)
        if key not in ufo_anchors:
            missing.append(key)
            return m.group(0)
        x, y = ufo_anchors[key]
        updated_count += 1
        return f"{prefix}{int(round(x))} {int(round(y))}{suffix}"

    new_text = MARKCLASS_RE.sub(repl_markclass, fea_text)
    new_text = POSBASE_RE.sub(repl_posbase, new_text)
    return new_text, updated_count, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ufo_path")
    ap.add_argument("fea_path")
    ap.add_argument("--out", default="synced.fea")
    args = ap.parse_args()

    ufo_anchors = load_ufo_anchors(Path(args.ufo_path))
    fea_text = Path(args.fea_path).read_text(encoding="utf-8")

    new_text, updated_count, missing = sync_fea_text(fea_text, ufo_anchors)

    Path(args.out).write_text(new_text, encoding="utf-8")
    print(f"Updated {updated_count} anchor coordinate(s) in place.")
    if missing:
        print(f"\n{len(missing)} (glyph, anchor) pair(s) referenced in the fea "
              f"were NOT found in the UFO (left unchanged):")
        for glyph, anchor in missing:
            print(f"  - {glyph}: {anchor}")
    print(f"\nWrote: {args.out}")


if __name__ == "__main__":
    main()
