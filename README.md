# FFB — Font Feature Builder

Generate OpenType features for **decomposed ("skeleton + marks") Arabic-script fonts** from a UFO.

Encoded letters (e.g. `beh-ar`) stay empty. At run time GSUB replaces them with a dotless skeleton glyph plus mark glyphs, and GPOS positions the marks from anchors. The glyph count does not explode with every dotted letter, and the designer only draws skeletons, marks and anchors.

Read the idea and its background in [docs/article.md](docs/article.md). Step-by-step usage is in the [user guide (فارسی)](docs/user-guide.fa.md).

## What works today

| Feature | Tool |
|---|---|
| GSUB `isol/init/medi/fina` from a letter → skeleton + marks table | `extract_decompose_table.py`, `generate_gsub.py` |
| GPOS `mark` and `mkmk` from anchors | `generate_gpos_mark.py` |
| GPOS `curs` from `Ex` / `_Ex` anchors | `generate_curs.py` |
| Rename FontLab-style anchor names to the convention | `normalize_anchors.py` |
| Update anchor coordinates (`mark`, `mkmk`, `curs`) in an existing `.fea` from the UFO | `sync_anchor_coords.py`, or the browser tool `tools/anchor_sync_tool.html` (no install) |
| UFO → `.otf` compiler (CFF) | `build_otf.py` |
| Everything above in one command | `ffb.py` |

Planned: `calt`/`rclt`, automatic kerning, contextual mark shifts.

## Quick start

```
pip install fonttools
python3 src/ffb.py MyFont.ufo --out build/
```

`MyFont.ufo` may be a folder or a `.zip`. Output: `build/MyFont.otf` plus the generated `.fea` files.

No command line? Use `tools/anchor_sync_tool.html`: open it in a browser (it needs an internet connection once, to load JSZip), drop in your UFO zip, and copy the updated feature code.

## The FFB convention (what your font must follow)

FFB is **not font-agnostic**: it reads names. Any font that follows these conventions works.

- **Anchors on marks** start with `_` and name the slot they attach to; **anchors on bases** carry the slot name without `_`.
  Slots: `Tm` (top mark), `Bm` (bottom mark), `ring`, `sarkesh`, `bar`.
- **Cursive attachment:** `Ex` (exit) and `_Ex` (entry). `init` has `Ex` only, `medi` both, `fina` `_Ex` only, `isol` none.
- A mark that has both `_Bm` and `Bm` hosts further marks and is routed to `mkmk`.
- **Glyph names:** encoded letters `name-ar`; skeletons `name.isol|init|medi|fina.skl`; marks `name.mrk` (older exports: `name.mrk.skl`). The GPOS generators recognise marks by their `_` anchors, not by the suffix.
- **Decomposition table:** one entry per encoded letter and form, see [examples/decompose_table.example.yaml](examples/decompose_table.example.yaml).

`normalize_anchors.py` renames the variants FontLab produces (`t.X.mrk.skl`, `b.X.mrk`, `m.ring.mrk`, `_T.mrk`, and the single-letter `T/B/D/R/S` slots) to the convention, and drops duplicate anchors that result.

## Repository layout

```
src/            the tools (Python)
tools/          anchor_sync_tool.html — browser tool, no install
templates/      simple_kern_template.fea
examples/       example decomposition table
sample-font/    FFB_Master.otf, its UFO source and the generated features
docs/           article, user guide, specification
```

## Status and caveats

- Validated on one font family so far. Reports from other designers are welcome.
- Not yet resolved: reliable behaviour in Word/InDesign for every decomposed font, sukun on stacked marks (`mkmk`), and the planned features above.
- `build_otf.py` is a small purpose-built compiler (CFF only). It needs closed outlines and refuses UFOs with open contours (single-line fonts). If you prefer, use the generated `.fea` files with your own pipeline (FontLab, ufo2ft, fontmake).

## License

Code: MIT, see [LICENSE](LICENSE). The sample font has its own licence, see [sample-font/README.md](sample-font/README.md).
