"""
normalize_anchors.py

Renames anchors inside a UFO from whatever a font editor (e.g. FontLab)
generated into the project's simple naming convention:

    Tm / _Tm             top mark
    Bm / _Bm             bottom mark
    ring / _ring         ring modifier
    sarkesh / _sarkesh   stroke that turns kaf into gaf
    bar / _bar           stroke used e.g. for reh/waw/lam variants
    Ex / _Ex             cursive attachment (Ex = exit/offered, _Ex = entry/received)

Anchors that don't match any known Arabic-skeleton pattern (e.g. Latin/
Cyrillic diacritic anchors on non-Arabic glyphs) are left untouched.

Only depends on fontTools (no defcon / external UFO library needed) --
reads glyph anchors via fontTools.ufoLib.glifLib and rewrites the .glif
XML directly.

Usage:
    python3 normalize_anchors.py <path-to-ufo> [--dry-run] [--out OUT_UFO]
"""

import argparse
import re
import shutil
from pathlib import Path

from fontTools.ufoLib.glifLib import GlyphSet


# ---------------------------------------------------------------------------
# Mapping rules
# ---------------------------------------------------------------------------
BASE_RULES = [
    # Specific stroke names MUST be checked before the generic t./b. mark
    # patterns below, since "t.<anything>.mrk(.skl)?" would otherwise also
    # swallow "t.sarkesh.mrk(.skl)?" and "t.bar.mrk(.skl)?".
    # The ".skl" suffix is optional: some exports name the anchor after the
    # glyph's own name, which may or may not carry ".skl" itself. Numeric
    # suffixes can chain (e.g. "_1_2" for deep mark-on-mark-on-mark stacking).
    # FontLab has been observed renaming these anchors differently across
    # exports (t.X.mrk.skl, t.X.mrk, m.X.mrk_N, a1, ...) -- each new pattern
    # discovered gets its own rule here rather than requiring manual fixing.
    (re.compile(r"^[tbm]\.sarkesh\.mrk(?:\.skl)?((?:_\d+)*)$"), r"sarkesh\1"),
    (re.compile(r"^[tbm]\.bar\.mrk(?:\.skl)?(?:_\d+)*$"), r"bar"),
    (re.compile(r"^t\..+\.mrk(?:\.skl)?((?:_\d+)*)$"), r"Tm\1"),
    (re.compile(r"^t\..+\.mrk\.skl\.\d+$"), r"Tm"),  # e.g. t.damma.mrk.skl.1
    (re.compile(r"^b\..+\.mrk(?:\.skl)?((?:_\d+)*)$"), r"Bm\1"),
    (re.compile(r"^ring$"), r"ring"),
    (re.compile(r"^m\.ring\.mrk((?:_\d+)*)$"), r"ring\1"),
    # Cursive attachment: confirmed by designer -- init glyphs carry only
    # "E" (exit), medi carries both "E" and "_E", fina carries only "_E",
    # isol carries neither. Same pattern applies to ss## stylistic variants.
    (re.compile(r"^E$"), r"Ex"),
]

MARK_SIDE_RULES = [
    (re.compile(r"^_" + p.pattern[1:]), r"_" + repl) for p, repl in BASE_RULES
]

# Mark-side names written with a capital slot letter and a ".mrk" (or the
# typo ".mek") suffix, e.g. "_T.mrk", "_B.mrk": FontLab's way of naming the
# mark half of the pair whose base half is "t.<glyph>.mrk" / "b.<glyph>.mrk".
EXTRA_MARK_RULES = [
    (re.compile(r"^_T\.(?:mrk|mek)((?:_\d+)*)$"), r"_Tm\1"),
    (re.compile(r"^_B\.(?:mrk|mek)((?:_\d+)*)$"), r"_Bm\1"),
]

# Single-letter slot names from FontLab-generated feature code:
#   T/_T top marks, B/_B bottom marks, D/_D bar, R/_R ring, S/_S sarkesh.
# After renaming, a glyph may carry the same anchor twice (e.g. "_T" and
# "_T.mrk" both become "_Tm"); duplicates are dropped when rewriting.
SLOT_LETTER_RULES = []
for _letter, _slot in (("T", "Tm"), ("B", "Bm"), ("D", "bar"), ("R", "ring"), ("S", "sarkesh")):
    SLOT_LETTER_RULES.append((re.compile(r"^_" + _letter + r"$"), "_" + _slot))
    SLOT_LETTER_RULES.append((re.compile(r"^" + _letter + r"$"), _slot))

ALL_RULES = EXTRA_MARK_RULES + MARK_SIDE_RULES + BASE_RULES + SLOT_LETTER_RULES


def normalize_name(name: str) -> str:
    for pattern, repl in ALL_RULES:
        if pattern.match(name):
            return pattern.sub(repl, name)
    return name


# ---------------------------------------------------------------------------
# UFO glif-level anchor scan / rewrite
# ---------------------------------------------------------------------------
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


def scan_ufo_anchors(ufo_path: Path):
    glyphs_dir = ufo_path / "glyphs"
    layercontents = ufo_path / "layercontents.plist"
    layer_dirs = [glyphs_dir] if glyphs_dir.exists() else []
    if layercontents.exists():
        import plistlib
        with open(layercontents, "rb") as f:
            layers = plistlib.load(f)
        layer_dirs = [ufo_path / d for _, d in layers if (ufo_path / d).exists()]

    result = {}
    for layer_dir in layer_dirs:
        gs = GlyphSet(str(layer_dir))
        for glyph_name in gs.keys():
            collector = _AnchorCollector()
            gs.readGlyph(glyph_name, collector)
            names = [a.get("name") for a in collector.anchors if a.get("name")]
            if names:
                result.setdefault(glyph_name, []).extend(names)
    return result


def rewrite_ufo_anchors(src_ufo: Path, dst_ufo: Path, mapping: dict):
    if dst_ufo.exists():
        shutil.rmtree(dst_ufo)
    shutil.copytree(src_ufo, dst_ufo)

    anchor_name_re = re.compile(r'(<anchor\b[^>]*\bname=")([^"]+)(")')

    def repl(m):
        old = m.group(2)
        new = mapping.get(old, old)
        return f"{m.group(1)}{new}{m.group(3)}"

    anchor_el_re = re.compile(r'[ \t]*<anchor\b[^>]*/>[ \t]*\n?')
    attr_re = re.compile(r'\b(x|y|name)="([^"]*)"')

    def dedupe(text, glif_name):
        seen = {}
        def drop(m):
            a = dict(attr_re.findall(m.group(0)))
            key = a.get("name")
            if key in seen:
                if seen[key] != (a.get("x"), a.get("y")):
                    print(f"  WARNING {glif_name}: duplicate anchor {key} with different "
                          f"coordinates {seen[key]} vs {(a.get('x'), a.get('y'))}; kept the first")
                return ""
            seen[key] = (a.get("x"), a.get("y"))
            return m.group(0)
        return anchor_el_re.sub(drop, text)

    changed_files = 0
    for glif in dst_ufo.glob("**/*.glif"):
        text = glif.read_text(encoding="utf-8")
        new_text = dedupe(anchor_name_re.sub(repl, text), glif.name)
        if new_text != text:
            glif.write_text(new_text, encoding="utf-8")
            changed_files += 1
    return changed_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ufo_path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="output UFO path (defaults to <input>.normalized.ufo)")
    args = ap.parse_args()

    ufo_path = Path(args.ufo_path)
    per_glyph = scan_ufo_anchors(ufo_path)

    all_names = sorted({name for names in per_glyph.values() for name in names})
    mapping = {name: normalize_name(name) for name in all_names}
    unchanged = sorted(n for n, new in mapping.items() if new == n)
    changed_names = {n: new for n, new in mapping.items() if new != n}

    print(f"Found {len(all_names)} distinct anchor names across {len(per_glyph)} glyphs\n")
    print(f"{'OLD NAME':40s} -> NEW NAME")
    print("-" * 70)
    for old in all_names:
        new = mapping[old]
        marker = "" if new != old else "  (unchanged)"
        print(f"{old:40s} -> {new}{marker}")

    if unchanged:
        print(f"\n{len(unchanged)} anchor name(s) did not match any Arabic-skeleton "
              f"pattern and were left as-is (review manually):")
        for name in unchanged:
            print(f"  - {name}")

    total_occurrences = sum(
        1 for names in per_glyph.values() for n in names if n in changed_names
    )
    print(f"\n{total_occurrences} individual anchor occurrence(s) across all glyphs "
          f"would be renamed ({len(changed_names)} distinct names).")

    if not args.dry_run:
        out_path = Path(args.out) if args.out else ufo_path.with_name(
            ufo_path.stem + ".normalized" + ufo_path.suffix
        )
        n_files = rewrite_ufo_anchors(ufo_path, out_path, mapping)
        print(f"\nRewrote anchors in {n_files} .glif file(s).")
        print(f"Saved normalized UFO to: {out_path}")


if __name__ == "__main__":
    main()
