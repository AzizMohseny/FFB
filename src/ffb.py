#!/usr/bin/env python3
"""
ffb.py -- one-command pipeline: UFO -> features -> OpenType (.otf)

    python3 ffb.py MyFont.ufo            (a folder or a .zip of the UFO)
    python3 ffb.py MyFont.ufo --out build/

Steps (each is also available as its own script in this folder):
  1. normalize_anchors   rename FontLab-style anchor names to the FFB convention
  2. extract/generate    GSUB isol/init/medi/fina (from --table, or from the
                         UFO's features.fea if no table is given)
  3. generate_gpos_mark  GPOS mark + mkmk
  4. generate_curs       GPOS curs
  5. build_otf           compile everything into an OTF

Requires:  pip install fonttools
"""
import argparse, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(script, *args):
    cmd = [sys.executable, str(HERE / script), *map(str, args)]
    print("\n>>", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"Step failed: {script}")


def find_ufo(root: Path) -> Path:
    if root.suffix == ".ufo":
        return root
    hits = list(root.rglob("*.ufo"))
    if not hits:
        sys.exit("No .ufo folder found inside the zip.")
    return hits[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ufo", help="UFO folder or .zip containing one")
    ap.add_argument("--out", default="ffb_build", help="output folder (default: ffb_build)")
    ap.add_argument("--table", help="decomposition table (.yaml); default: extract from features.fea")
    ap.add_argument("--no-normalize", action="store_true", help="skip anchor renaming")
    ap.add_argument("--extra-fea", nargs="*", default=[], help="extra .fea files to append (e.g. kern, calt)")
    a = ap.parse_args()

    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    src = Path(a.ufo).resolve()
    work = Path(tempfile.mkdtemp(prefix="ffb_"))
    if src.suffix == ".zip":
        with zipfile.ZipFile(src) as z:
            z.extractall(work / "in")
        ufo = find_ufo(work / "in")
    else:
        ufo = src
    name = ufo.stem.replace(".normalized", "")

    if not a.no_normalize:
        norm = out / f"{name}.normalized.ufo"
        if norm.exists():
            shutil.rmtree(norm)
        run("normalize_anchors.py", ufo, "--out", norm)
        ufo = norm

    table = Path(a.table) if a.table else out / "decompose_table.yaml"
    if not a.table:
        run("extract_decompose_table.py", ufo / "features.fea", "--out", table)
    gsub, mark, curs = out / "gsub.fea", out / "gpos_mark.fea", out / "gpos_curs.fea"
    run("generate_gsub.py", table, "--out", gsub)
    run("generate_gpos_mark.py", ufo, "--out", mark)
    run("generate_curs.py", ufo, "--out", curs)
    otf = out / f"{name}.otf"
    run("build_otf.py", ufo, gsub, mark, curs, *a.extra_fea, "--out", otf)
    print(f"\nDone. Font: {otf}\nFeature files are in {out}")


if __name__ == "__main__":
    main()
