"""
generate_gpos_mark.py

Generates GPOS `mark` and `mkmk` feature blocks directly from UFO anchors,
using the project's normalized naming convention:

    base glyph anchor:   Tm, Bm_1, sarkesh, ring, bar, Ex   (no "_" prefix)
    mark glyph anchor:   _Tm, _Bm_1, _sarkesh, _ring, _bar, _Ex

For `mark`: any anchor pair (X / _X) where the mark-side glyph is not
itself a base for that same slot becomes a MarkToBase attachment.

For `mkmk`: when a mark glyph ALSO exposes a same-named anchor without
the "_" prefix (i.e. it can itself host another mark, for stacking), that
pair becomes a MarkToMark attachment instead.

Ex/_Ex (cursive) and kerning are handled by separate generators -- this
module only covers mark/mkmk.

Usage:
    python3 generate_gpos_mark.py <path-to-normalized-ufo> [--out mark.fea]
"""

import argparse
from collections import defaultdict
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


def scan_anchors(ufo_path: Path):
    """Return {glyph_name: [{"name":..., "x":..., "y":...}, ...]}"""
    glyphs_dir = ufo_path / "glyphs"
    result = {}
    gs = GlyphSet(str(glyphs_dir))
    for glyph_name in gs.keys():
        collector = _AnchorCollector()
        gs.readGlyph(glyph_name, collector)
        if collector.anchors:
            result[glyph_name] = collector.anchors
    return result


CURSIVE_NAMES = {"Ex"}  # handled by a separate curs generator, skip here


def build_mark_data(per_glyph: dict):
    """
    Returns:
        base_anchors: {anchor_slot: {glyph: (x, y)}}      -- e.g. slot "Tm"
        mark_anchors: {anchor_slot: {glyph: (x, y)}}       -- glyphs with "_Tm"
        mark_can_host: {glyph: {slot: (x, y)}}             -- marks that ALSO
                                                               expose a base
                                                               anchor (for mkmk)
    """
    base_anchors = defaultdict(dict)
    mark_anchors = defaultdict(dict)

    for glyph, anchors in per_glyph.items():
        for a in anchors:
            name = a.get("name")
            if not name:
                continue
            x, y = a.get("x", 0), a.get("y", 0)
            if name.startswith("_"):
                slot = name[1:]
                if slot in CURSIVE_NAMES:
                    continue
                mark_anchors[slot][glyph] = (x, y)
            else:
                if name in CURSIVE_NAMES:
                    continue
                base_anchors[name][glyph] = (x, y)

    # A glyph is a "mark glyph" for mkmk purposes if it has at least one
    # "_slot" anchor (i.e. it attaches to something). Such a glyph might
    # ALSO expose a plain "slot" anchor of its own, meaning another mark
    # can stack on top of it.
    mark_glyphs = {g for anchors in mark_anchors.values() for g in anchors}
    mark_can_host = defaultdict(dict)
    for slot, glyphs in base_anchors.items():
        for g, xy in glyphs.items():
            if g in mark_glyphs:
                mark_can_host[g][slot] = xy

    return base_anchors, mark_anchors, mark_can_host


def fea_anchor(xy):
    if xy is None:
        return "<anchor NULL>"
    x, y = xy
    return f"<anchor {int(round(x))} {int(round(y))}>"


def generate_mark_feature(base_anchors, mark_anchors, mark_can_host, feature_tag="mark", emitted_classes=None):
    """
    feature_tag = "mark"  -> MarkToBase: bases are glyphs in base_anchors
                              MINUS glyphs that are themselves marks
                              (those are handled by mkmk instead).
    feature_tag = "mkmk"  -> MarkToMark: bases are entries in mark_can_host.

    emitted_classes: a set of markClass names already declared elsewhere in
    the file (markClass namespaces are GLOBAL in feaLib, not per-lookup, so
    each glyph/class pair may only be declared once across the whole file).

    Each slot gets its OWN lookup. This matters most for mkmk: a mark glyph
    that itself hosts another mark can carry anchors for more than one slot
    (e.g. both "_Bm_1" and "_Bm_1_2" for deep stacking) -- feaLib does not
    allow one glyph to belong to two mark classes used within the same
    lookup, so slots must be split across lookups to avoid that conflict.
    """
    if emitted_classes is None:
        emitted_classes = set()

    lines = [f"feature {feature_tag} {{"]
    lines.append(f"  # GPOS feature: {'Mark Positioning' if feature_tag == 'mark' else 'Mark-to-Mark Positioning'}")
    lines.append("  # auto-generated from UFO anchors -- do not hand-edit")
    lines.append("")

    slots_used = []
    for slot in sorted(mark_anchors):
        if feature_tag == "mark" and slot not in base_anchors:
            continue
        if feature_tag == "mkmk" and not any(slot in hosts for hosts in mark_can_host.values()):
            continue
        slots_used.append(slot)

    for slot in slots_used:
        lookup_name = f"{feature_tag}_auto_{slot}"
        lines.append(f"  lookup {lookup_name} {{")
        if slot not in emitted_classes:
            for mark_glyph, xy in sorted(mark_anchors[slot].items()):
                lines.append(f"    markClass {mark_glyph} {fea_anchor(xy)} @{slot};")
            emitted_classes.add(slot)

        if feature_tag == "mark":
            base_set = {
                g: xy for g, xy in base_anchors.get(slot, {}).items()
                if g not in mark_can_host
            }
            verb = "pos base"
        else:
            base_set = {
                g: anchors[slot] for g, anchors in mark_can_host.items() if slot in anchors
            }
            verb = "pos mark"

        for glyph, xy in sorted(base_set.items()):
            lines.append(f"    {verb} {glyph} {fea_anchor(xy)} mark @{slot};")

        lines.append(f"  }} {lookup_name};")
        lines.append("")

    lines.append(f"}} {feature_tag};")
    return "\n".join(lines)


def _regroup_by_glyph(base_anchors, slots_used):
    out = defaultdict(dict)
    for slot in slots_used:
        for glyph, xy in base_anchors.get(slot, {}).items():
            out[glyph][slot] = xy
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ufo_path")
    ap.add_argument("--out", default="generated_gpos_mark.fea")
    args = ap.parse_args()

    ufo_path = Path(args.ufo_path)
    per_glyph = scan_anchors(ufo_path)
    base_anchors, mark_anchors, mark_can_host = build_mark_data(per_glyph)

    emitted_classes = set()
    mark_fea = generate_mark_feature(base_anchors, mark_anchors, mark_can_host, "mark", emitted_classes)
    mkmk_fea = generate_mark_feature(base_anchors, mark_anchors, mark_can_host, "mkmk", emitted_classes)

    out_text = mark_fea + "\n\n" + mkmk_fea + "\n"
    Path(args.out).write_text(out_text, encoding="utf-8")

    print(f"Base anchor slots found: {sorted(base_anchors.keys())}")
    print(f"Mark anchor slots found: {sorted(mark_anchors.keys())}")
    print(f"Mark glyphs that can host another mark (mkmk): {sorted(mark_can_host.keys())}")
    print(f"\nWrote: {args.out}")


if __name__ == "__main__":
    main()
