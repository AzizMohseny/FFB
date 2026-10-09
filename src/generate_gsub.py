"""
generate_gsub.py

Turns the decomposition table (spec section 3; produced either by hand or
by extract_decompose_table.py) into real GSUB `isol`/`init`/`medi`/`fina`
feature blocks in .fea syntax.

This is the "forward" direction: table -> features.fea, the reverse of
extract_decompose_table.py. Running extract then generate on the same
font and diffing the two features.fea files is the sanity check that the
round-trip is faithful.

Usage:
    python3 generate_gsub.py <decompose_table.yaml> [--out generated_gsub.fea]
"""

import argparse
from pathlib import Path

import yaml

FORM_ORDER = ("isol", "init", "medi", "fina")

FEATURE_HEADER = {
    "isol": "Isolated Forms",
    "init": "Initial Forms",
    "medi": "Medial Forms",
    "fina": "Final Forms",
}


def generate_fea(table: dict) -> str:
    lines = []
    for form in FORM_ORDER:
        entries = [
            (encoded, forms[form])
            for encoded, forms in sorted(table.items())
            if form in forms
        ]
        if not entries:
            continue
        lines.append(f"feature {form} {{")
        lines.append(f"  # GSUB feature: {FEATURE_HEADER[form]}")
        lines.append(f"  # auto-generated from decomposition table -- do not hand-edit")
        lines.append("")
        for encoded_glyph, replacement in entries:
            seq = " ".join(replacement)
            lines.append(f"  sub {encoded_glyph} by {seq};")
        lines.append(f"}} {form};")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table_path")
    ap.add_argument("--out", default="generated_gsub.fea")
    args = ap.parse_args()

    with open(args.table_path, encoding="utf-8") as f:
        table = yaml.safe_load(f)

    fea_text = generate_fea(table)
    Path(args.out).write_text(fea_text, encoding="utf-8")

    n_rules = sum(len(forms) for forms in table.values())
    print(f"Generated {n_rules} substitution rules across "
          f"{sum(1 for form in FORM_ORDER if any(form in f for f in table.values()))} "
          f"features, from {len(table)} encoded letters.")
    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
