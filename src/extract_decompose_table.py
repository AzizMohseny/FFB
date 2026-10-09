"""
extract_decompose_table.py

Reverse-engineers the "encoded letter -> skeleton + mark sequence" GSUB
decomposition table (spec section 3) out of a FontLab-generated
features.fea, and writes it as a portable YAML file that sits next to the
UFO (not inside it) -- independent of any particular font editor.

This does NOT generate anything new; it recovers data that currently only
exists baked into FontLab's compiled fea output, so it can become the
single source of truth the builder reads from instead.

Usage:
    python3 extract_decompose_table.py <path-to-features.fea> [--out table.yaml]
"""

import argparse
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # fall back to a minimal writer if PyYAML isn't installed


FEATURE_TO_FORM = {
    "isol": "isol",
    "init": "init",
    "medi": "medi",
    "fina": "fina",
}

# Matches lines like:  sub beh-ar by behDotless.init.skl dotbelow.mrk.skl;
# Trailing comments after the ';' (e.g. "; # U+0628") are tolerated and ignored.
SUB_RE = re.compile(r"^\s*sub\s+(\S+)\s+by\s+([^;]+);\s*(?:#.*)?$")

# Matches the start of a feature block: feature isol {
FEATURE_START_RE = re.compile(r"^\s*feature\s+(\w+)\s*\{")
FEATURE_END_RE = re.compile(r"^\s*\}\s*\w*\s*;")


def parse_fea(fea_text: str):
    """Return {encoded_glyph: {form: [glyph, ...]}} for isol/init/medi/fina."""
    table = {}
    current_feature = None
    depth = 0

    for raw_line in fea_text.splitlines():
        line = raw_line.strip()

        m = FEATURE_START_RE.match(line)
        if m:
            tag = m.group(1)
            current_feature = tag if tag in FEATURE_TO_FORM else None
            depth = 1
            continue

        if current_feature is not None:
            if FEATURE_END_RE.match(line):
                current_feature = None
                depth = 0
                continue

            sub_m = SUB_RE.match(line)
            if sub_m:
                encoded_glyph = sub_m.group(1)
                replacement = sub_m.group(2).split()
                form = FEATURE_TO_FORM[current_feature]
                table.setdefault(encoded_glyph, {})[form] = replacement

    return table


def write_yaml(table: dict, out_path: Path):
    if yaml is not None:
        # Keep forms in a stable, readable order: isol, init, medi, fina
        ordered = {}
        for glyph in sorted(table):
            forms = table[glyph]
            ordered[glyph] = {
                form: forms[form]
                for form in ("isol", "init", "medi", "fina")
                if form in forms
            }
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(ordered, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=None)
    else:
        # Minimal hand-rolled YAML writer, no external dependency required.
        with open(out_path, "w", encoding="utf-8") as f:
            for glyph in sorted(table):
                f.write(f"{glyph}:\n")
                forms = table[glyph]
                for form in ("isol", "init", "medi", "fina"):
                    if form in forms:
                        seq = ", ".join(forms[form])
                        f.write(f"  {form}: [{seq}]\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fea_path")
    ap.add_argument("--out", default="decompose_table.yaml")
    args = ap.parse_args()

    fea_text = Path(args.fea_path).read_text(encoding="utf-8")
    table = parse_fea(fea_text)

    n_forms = sum(len(forms) for forms in table.values())
    print(f"Extracted {len(table)} encoded letters, {n_forms} total form entries "
          f"(isol/init/medi/fina combined).")

    incomplete = [g for g, forms in table.items() if len(forms) < 4]
    if incomplete:
        print(f"\n{len(incomplete)} letter(s) have fewer than 4 forms "
              f"(expected for non-joining letters like alef/dal/reh/waw, "
              f"but worth a manual glance otherwise):")
        for g in sorted(incomplete):
            print(f"  - {g}: has {sorted(table[g].keys())}")

    write_yaml(table, Path(args.out))
    print(f"\nWrote decomposition table to: {args.out}")


if __name__ == "__main__":
    main()
