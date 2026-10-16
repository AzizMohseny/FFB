# FFB User Guide

This guide is for a type designer who has designed skeletons and marks in a UFO and wants the features to be generated mechanically. No programming knowledge is required. There are three paths; start with the simplest.

## 1. Before anything else: the FFB convention

FFB reads names. If names do not match the convention, the program will find nothing or will error out. If your font matches the reference font, all capabilities available in FFB will be used.

**Glyph names**

| Type | Format | Example |
|---|---|---|
| Encoded letter (empty) | `name-ar` | `beh-ar` |
| Skeleton | `name.form.skl` (form: isol, init, medi, fina) | `behDotless.init.skl` |
| Mark | `name.mrk` (in older outputs `name.mrk.skl`) | `dotbelow.mrk` |

Marks are recognized by the GPOS generators from their `_` anchor, not from the name suffix; the suffix is only for readability.

**Anchor names**

| Anchor | Where | Meaning |
|---|---|---|
| `T` / `_T` | base / mark | top mark |
| `B` / `_B` | base / mark | bottom mark |
| `R` / `_R` | base / mark | ring |
| `S` / `_S` | base / mark | sarkesh (gaf) |
| `D` / `_D` | base / mark | bar |
| `E` / `_E` | skeleton | cursive attachment: exit and entry |

Rules:

- A **mark** anchor starts with `_`, a **base** anchor does not. Paired anchors must share the same name.
- A mark that has both `_B` and `B` is itself a host for another mark and goes to `mkmk`.
- Cursive attachment: `init` has only `E`; `medi` has both; `fina` has only `_E`; `isol` has neither.
- Non-joining letters (alef, dal, re, waw, zhe, ...) have only `isol` and `fina`.

**FontLab** renames anchors when opening a file (for example `t.dotbelow.mrk.skl`). The script `normalize_anchors.py` restores these names to the ones above, and `ffb.py` runs it automatically. Single-letter names `T/B/D/R/S` and forms like `_T.mrk` are also recognized (`T`→`Tm`, `B`→`Bm`, `D`→`bar`, `R`→`ring`, `S`→`sarkesh`). If a glyph ends up with two anchors of the same name after renaming, the second is removed, and if their coordinates differ, a warning is issued.

## 2. Path A (no installation): anchor sync tool

For when you already have a GPOS feature and only the anchor coordinates in the UFO have changed. This tool updates the coordinates of `mark`, `mkmk` and `curs`, and recognizes FontLab names like `t.fatha.mrk`, `_T.mrk` and `T/B/D/R/S`. The final report shows what was not found in the UFO.

1. Open `tools/anchor_sync_tool.html` in a browser. Internet is needed only the first time.
2. Zip the UFO folder (the whole `.ufo` folder) and drop it on the page.
3. Read the report: how many anchors were changed and what was not found.
4. Click "Copy all" or copy the text from the box.
5. In FontLab, open the features panel, delete the old `mark`/`mkmk` feature and paste the new text. Pasting does not rename anchors, because the text contains only numbers and glyph names.

## 3. Path B: full font build with one command

This path builds GSUB and GPOS and produces an `.otf` file. One-time installation, then a single command line.

**Installation (first time only):**

1. Install Python 3 from python.org. On Windows, tick "Add Python to PATH".
2. In a terminal (on Windows, Command Prompt): `pip install fonttools`

**Build the font:**

```
python src/ffb.py MyFont.ufo --out build
```

`MyFont.ufo` can be a folder or a zip file. The `build` folder will contain:

| File | Contents |
|---|---|
| `MyFont.otf` | final font |
| `gsub.fea` | isol, init, medi, fina |
| `gpos_mark.fea` | mark and mkmk |
| `gpos_curs.fea` | curs |
| `decompose_table.yaml` | "letter → skeleton + mark" table |
| `*.normalized.ufo` | UFO with normalized anchor names |

If you have edited the decomposition table by hand: add `--table my_table.yaml`. Add other features (e.g. kern) with `--extra-fea kern.fea`.

## 4. Path C: only .fea files for FontLab

Paste `build/gsub.fea`, `build/gpos_mark.fea` and `build/gpos_curs.fea` separately into FontLab (or another tool) and build the font yourself.

## 5. Decomposition table (which letter goes to which skeleton and which mark)

The file `examples/decompose_table.example.yaml` is a sample. Each letter has one entry:

```
noon-ar:
  isol: [noon.isol.skl, dotabove.mrk.skl]
  init: [behDotless.init.skl, dotabove.mrk.skl]
  medi: [behDotless.medi.skl, dotabove.mrk.skl]
  fina: [noon.fina.skl, dotabove.mrk.skl]
```

For a new language (Kurdish, Urdu, Pashto, Uyghur), add the new letters to this table. The skeleton and mark must exist in the UFO. The reference font contains all glyphs related to the languages of the Arabic script, and a font prepared on its basis supports all languages of this script. (All Unicode codes are included, but this requires testing and debugging.)

## 6. Simple kerning (non-joining letters)

See the template `templates/simple_kern_template.fea`. Each line is one rule:

```
pos alef.fina.skl dotbelow.mrk <100 -30 0 0>;
```

- Order: **skeleton first, mark second.** The reverse order is never applied.
- The four numbers are, in order: xPlacement, yPlacement, xAdvance, yAdvance. To shift a mark, you usually change only the first two.
- The feature name is `kern`.

### Advanced kerning: context-dependent shifting

The reference font provides a sample of advanced kerning for dots. This sample shows how a mark can be shifted only in a specific context. The three lookups below are defined **before** `feature kern` and called **inside** it:

```
lookup shiftThreeDotsLeft {
    pos @below' <-100 0 0 0>;
} shiftThreeDotsLeft;

lookup contextShiftThreeDots {
    pos reh.isol.skl behDotless.init.skl @below' lookup shiftThreeDotsLeft;
} contextShiftThreeDots;

lookup contextShiftAbove {
    pos dotabove.mrk behDotless.init.skl @below' lookup shiftThreeDotsLeft;
} contextShiftAbove;

feature kern {
    # simple kerning rules
    pos alef.fina.skl dotbelow.mrk <100 -30 0 0>;

    # call context-dependent lookups
    lookup contextShiftThreeDots;
    lookup contextShiftAbove;
} kern;
```

- `shiftThreeDotsLeft` performs the shift itself (100 units to the left).
- `contextShiftThreeDots` says this shift should only be applied when `reh.isol.skl` and `behDotless.init.skl` precede the `@below` mark.
- `contextShiftAbove` does the same for the `dotabove.mrk` context.

You can repeat this pattern for any letter-and-mark combination you need.

## 7. Common problems

| Symptom | Cause and solution |
|---|---|
| Error `Glyph ... already defined` | A mark is defined twice in one class, or two anchors share a name (e.g. two `_Tm`). Delete one in the UFO. |
| A mark does not attach anywhere | Its anchor has no `_`, or its base name does not match the mark name. Open `gpos_mark.fea` and check whether the glyph is there. |
| After opening in FontLab, anchors have different names | Run `normalize_anchors.py` (automatic with `ffb.py`). |
| Font does not install ("not a valid font") | CFF fonts must be `OTTO`. `build_otf.py` fixes this. |
| Word or InDesign shows the old font | Font cache. Rename the font's internal name, or uninstall the font and reinstall it, then close and reopen the application. |
| `curs` is empty | `Ex`/`_Ex` anchors are missing in the UFO. |
| The built font does not shape letters | Check that the isol/init/medi/fina features are in the `.otf` (using FontTools or FontLab). |
| `fatal error` in the `kern` feature | Lookups must be defined **before** `feature kern` and called **inside** it. If they are called outside the feature, FontLab raises an error. |

## 8. What is not yet automated

- `calt` and `rclt` (context-dependent substitutions)
- Automatic kerning and context-dependent mark shifting
- Full behaviour in Word and InDesign is not yet guaranteed for all fonts.

To report a problem, open an issue on GitHub and attach a small UFO or a list of glyphs.
