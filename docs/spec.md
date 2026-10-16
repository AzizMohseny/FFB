# FFB Technical Specification: An Arabic-Script Font Builder Based on a Skeletal Architecture

## 1. Introduction and Project Goal

Arabic fonts are among the most complex to design, because of the cursive nature of the script, the large number of context-dependent alternates, and more than a thousand years of calligraphic tradition. Common font editors often fail to generate GPOS tables (especially for marks and diacritics) correctly, or generate them with many errors; the current common workaround is to rebuild these tables by hand in Microsoft VOLT — a slow and tedious task.

The goal of this project is to build a **builder** called **FFB** (Font Feature Builder) that:

- takes a **UFO** file exported from a font editor,
- uses a "skeleton" layer and a set of rule tables defined by the designer,
- completes the **GSUB and GPOS** tables,
- and delivers a complete font.

FFB will be released as open source on GitHub; personal profit is not the goal.

**Audience:** type designers who have design skill but not an engineering background. No programming knowledge is required.

### 1.1. Conceptual Background

The concept of the "skeleton" (a dotless base letter plus modifier marks) is based on an official Unicode proposal from 2003 ("Proposal to encode productive Arabic-script modifier marks" — Kew, Mansour, Davis), which proposed a similar structure for modeling the Arabic script.

The conceptual article for FFB is described in `README.md`. This document is the technical specification for the builder.

### 1.2. Difference from ufo2ft

ufo2ft compiles the features already present in `features.fea`, whereas FFB generates the features themselves from the decomposition tables and rules. FFB can be used alongside ufo2ft (feeding it the `.fea` output) or work independently. For `mark`/`mkmk`/`curs` generation, FFB uses the same logic as ufo2ft (or calls it directly).

---

## 2. Skeletal Architecture and Anchor Convention

### 2.1. Architectural Principle

- **Encoded** glyphs (glyphs directly connected to a Unicode codepoint, such as the letter "beh") always remain **empty** — no outline, no component.
- All actual visual shaping is produced through **skeleton** glyphs (the dotless base shape of each letter, separated by isol/init/medi/fina) and **mark** glyphs (dots and other modifier marks).
- The composition of an encoded letter into a skeleton+mark sequence happens **only at runtime** (by the layout engine through GSUB) — **no precomposed or component-based glyph is added**. This is a deliberate decision to avoid "glyph explosion".
- Dots, like other marks, have their own independent glyph identity and are managed like other marks.

**Decomposition example:**

```
beh-ar  →  behDotless.init.skl  +  dotbelow.mrk.skl
```

### 2.2. Architectural Limitations

- In software that does not fully support GSUB (such as some older versions of Word), this approach may not work correctly.
- Search and text selection may point to the skeleton glyph, not the original letter.
- Font size may grow, because the GSUB tables become more complex.
- These limitations are discussed in more detail in section 9 (Limitations).

### 2.3. Anchor Naming Convention

Instead of the complex, automatic naming that font editors (such as FontLab) generate, this simple convention is used as the basis:

| Anchor type | On base glyph (skeleton) | On mark glyph | Description |
|---|---|---|---|
| Top mark | `T` | `_T` | Top mark — dot/diacritic above the letter |
| Bottom mark | `B` | `_B` | Bottom mark — dot/diacritic below the letter |
| Ring | `R` | `_R` | ARABIC MODIFIER RING ABOVE/BELOW (e.g. U+06C4, U+0689) |
| Sarkesh | `S` | `_S` | The extra stroke that turns kaf into gaf |
| Bar | `D` | `_D` | E.g. REH WITH STROKE (U+075B), LĀM WITH BAR (U+076A), WAW+bar (U+06C5) |
| Cursive attachment | `E` (exit) | `_E` (entry) | `E` is the point the glyph offers to the next glyph, `_E` is the point it receives from the previous glyph — both on the skeleton glyph itself (not a separate mark glyph) |
| Mark-to-mark | The base anchor name with `_` on the mark glyph itself | — | For stacking multiple marks |

The `_` prefix on a mark glyph is the only signal the builder uses to detect "this glyph has the role of a mark" — this is our own convention, not part of the official UFO/fontTools syntax (though similar to the common convention in open-source tools such as ufo2ft).

**Note:** Names such as `_T.mrk` are also recognized.

**Note on short and long names:** In this document, the short names `T`/`B`/`R`/`S`/`D`/`E` are used as the primary convention. The long names `Tm`/`Bm`/`ring`/`sarkesh`/`bar`/`Ex` (which appeared in earlier FFB documentation) are equivalents of the same names, and the builder recognizes both forms. In the examples of section 7, either form may appear.

---

## 3. GSUB Decomposition Table (Encoded Letter → Skeleton + Mark)

This table is an independent data source (suggested: a YAML/JSON file next to the UFO, not a component and not lib.plist) that specifies, for each encoded letter, into which sequence of skeleton + mark(s) — separated by isol/init/medi/fina — it should be decomposed.

**Sample:**

```yaml
beh-ar:
  isol: [behDotless.isol.skl, dotbelow.mrk.skl]
  init: [behDotless.init.skl, dotbelow.mrk.skl]
  medi: [behDotless.medi.skl, dotbelow.mrk.skl]
  fina: [behDotless.fina.skl, dotbelow.mrk.skl]
```

The builder reads this table and directly generates the GSUB rules in the `isol`/`init`/`medi`/`fina` features:

```fea
sub beh-ar by behDotless.init.skl dotbelow.mrk.skl;
```

**Reasons for choosing this method (instead of component or lib.plist):**

- It is independent of the font editor.
- It is diffable and reviewable on GitHub for other contributors.
- It can be reused between different fonts (that support the same language/script), because this mapping is essentially a linguistic/orthographic rule, not a design feature of a particular font.

### 3.1. Table Validation

The builder compares the table with the glyph list of the UFO. If a letter is missing from the table, or a glyph is missing from the UFO, it is listed in the error report. The `--strict` mode makes the builder stop if any glyph is missing.

### 3.2. Coverage of Other Languages

For a new language (Kurdish, Urdu, Pashto, Uyghur), add the new letters to this table. The reference font contains all glyphs related to the languages of the Arabic script. (All Unicode codes are included, but this requires testing and debugging.)

---

## 4. Contextual Rule Table (for `calt`/`rclt` Features)

### 4.1. Six-Cell Form

Each row of this table describes a contextual substitution rule with the following form:

| Left column (condition: before...) | Middle column (Sub / by) | Right column (condition: after...) |
|---|---|---|
| **Sub:** the previous condition glyph/class (optional) | **Sub:** the target glyph/class | **Sub:** the next condition glyph/class (optional) |
| **by:** the replacement of the previous condition (only if it too must change) | **by:** the replacement of the target | **by:** the replacement of the next condition (only if it too must change) |

**Rules for conversion to fea:**

- Any column whose second row is filled is marked with `'` in that position and gets its own `by` (that is, that glyph also actually changes).
- A column whose second row is empty remains only as raw context (without `'`).
- Note on the right-to-left direction: "before" in the logical sense of text order is the equivalent of **backtrack context** in fea; "after" is the equivalent of **lookahead context**.

**Simple example (context only, without changing the context):**

```fea
sub @P-ss01' yeh.fina.skl by @ss01;
```

**Complete example (changing three glyphs simultaneously):**

```fea
sub context1' by context1_sub target' by target_sub context2' by context2_sub;
```

### 4.2. Workflow

1. The designer fills the six-cell table (some cells may be null).
2. The builder previews the fea rule as a single line, based on the filled/empty cells.
3. The designer confirms.
4. The builder adds the rule to the `calt` or `rclt` feature.
5. **The order of rules in the feature must be controlled and validated** — because contextual rules are executed in the order they are written, and an earlier rule can change or nullify the input of a later rule.

### 4.3. Order Validation

The builder writes the rules into the feature in the order they appear in the table, and raises a warning if:

- Two rules conflict (the same target glyph in two rules with different contexts).
- A later rule changes the input of an earlier rule.
- A rule refers to a glyph that was removed in an earlier rule.

### 4.4. Interaction with `mark`/`mkmk`

The order in which features are applied in OpenType is important. `calt`/`rclt` must be applied **before** `mark`/`mkmk`, so that marks are placed on the final skeleton, not on a not-yet-substituted skeleton. The builder respects this order automatically in the fea file.

---

## 5. Automatic GPOS Generation from Anchors (mark / mkmk / curs)

- UFO anchors following the convention of section 2.3 (base without `_`, mark with `_`) are directly readable by the builder.
- The `mark` (mark-to-base attachment), `mkmk` (mark-on-mark stacking), and `curs` (bidirectional cursive attachment of skeletons) features are generated **completely automatically** from the coordinates of these anchors — no extra data is needed from the designer.
- This part can be implemented using logic similar to `ufo2ft` (or by calling it directly).

**Handling of unknown anchors and right-to-left:** If an anchor with a name outside the convention of section 2.3 is present in the UFO, the builder lists it in the warning report but ignores it (except in `--strict` mode). For `mark`/`mkmk`/`curs`, the builder automatically sets `lookupflag RightToLeft` in the feature.

---

## 6. Simple Kerning (Non-Joining Letters)

- Kerning in Arabic only makes sense between skeletons that are **not connected to the next** (not dual-joining — such as re, dal/dhal, alef, waw, zay) and the next skeleton; letters that connect to the next have their spacing managed by `curs`/`mark` anchors, not by kerning.
- This metadata (the joining type of each skeleton) is in any case needed to generate the GSUB `isol`/`init`/`medi`/`fina`; no separate data source is needed.
- The number of real kerning pairs is limited (under 200 pairs), so the standard UFO manual setting (`kerning.plist` + `public.kern1`/`public.kern2` groups in `groups.plist`) is sufficient; no automatic geometric calculation is needed.

**Sample from `simple_kern_template.fea`:**

```fea
pos alef.fina.skl dotbelow.mrk <100 -30 0 0>;
```

- Order: **skeleton first, mark second.** The reverse order is never applied.
- The four numbers are, in order: xPlacement, yPlacement, xAdvance, yAdvance.
- The feature name is `kern`.

---

## 7. Advanced Kerning: Context-Dependent Shifting of the Mark Itself (Contextual Mark Positioning)

In addition to the classic kerning of section 6 (between non-joining skeletons), in decomposed fonts — especially those that reproduce calligraphic styles such as Nastaliq — a second type of kerning is needed: **context-dependent shifting of the mark glyph itself** (not the base glyph).

### 7.1. Technical Mechanism

This is implemented with **GPOS Type 8 (Chaining Contextual Positioning)**: an outer lookup detects the condition (the preceding or following base glyph), and if the condition is met, runs a nested **Single Adjustment (Type 1)** lookup on the target mark glyph, which directly adds the horizontal and vertical shift values (dx, dy) — without creating a new glyph and without changing the base anchor.

```fea
# Nested lookup: shift the dot itself
lookup dotShift_afterAlef {
  pos dotabove.mrk.skl <100 -30 0 0>;
} dotShift_afterAlef;

# Outer lookup: condition + call to the shift
lookup ctxMarkPos {
  lookupflag IgnoreBaseGlyphs;
  pos alef.fina.skl dotabove.mrk.skl' lookup dotShift_afterAlef;
} ctxMarkPos;
```

`IgnoreBaseGlyphs` sits on the outer lookup; the context condition (e.g. `alef.fina.skl`) is still written explicitly in the rule and is the basis of detection. This flag only ensures that, when scanning the sequence to find the *target position of the shift*, other base glyphs that happen to be in the way are ignored, so that the shift always lands exactly on the mark.

### 7.2. Table Structure

| Context glyph/class (left or right) | Target mark glyph | Shift value (dx, dy) |
|---|---|---|

The dx/dy values are set manually by the designer, for each (context, mark) pair.

### 7.3. Sample from the Reference Font

The reference font provides a sample of advanced kerning for dots. The three lookups below are defined **before** `feature kern` and called **inside** it:

```fea
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

**Note on order:** context-dependent lookups must be defined **before** `feature kern` and called **inside** it. If they are called outside the feature, FontLab raises a `fatal error`. This pattern is respected in the reference-font sample.

### 7.4. Kerning Monitor Tool (Independent of the Builder)

To determine the dx/dy values precisely and without error, the builder should include an independent **visual tool** ("kerning monitor"):

- (In the manner of FontLab) the designer types a **real word** in a live preview and sees the actual sequence of rendered glyphs in that real context — not just an isolated pair out of context.
- The designer selects whichever glyph/mark is needed in that context and moves it with the **arrow keys** (not the mouse, for precision and measurability).
- Each key press = **1 font unit**; holding `Shift` = **10-unit** steps.
- The final value (dx, dy) is stored directly in the table of section 7.2.
- **Platform:** an independent, open-source desktop application (not an online service, to avoid hosting maintenance costs) — using the same Python stack as the rest of the builder (e.g. UI with PyQt/PySide).

This part of FFB is under development.

---

## 8. Line Justification and the jastyKhatt Library

### 8.1. Separation of Responsibilities

Line justification is not the font's job; it is the text engine's job. Separation of responsibilities is essential here:

**1. The font's responsibility: providing capacity.**
The font must provide alternate forms, controlled variability of forms, and the necessary facilities for preserving beauty and calligraphic rules.

**2. The justifier's responsibility: intelligent decision-making.**
The text engine must measure line length, evaluate the font's capacities, and decide on the place, type and amount of kashida.

**3. Beauty takes priority over mechanical solutions.**
Line justification should not be done merely by increasing word spacing. First, the calligraphic capacities of the script should be used; then, if needed, spacing should be adjusted in a limited way.

### 8.2. The jastyKhatt Library

For this purpose, FFB provides a JavaScript library called **jastyKhatt**, whose task is the intelligent use of kashida with an eye to Arabic calligraphic traditions.

jastyKhatt applies line justification in layers with a defined priority:

**Layer 1: Applying kashida forms with variable alternate forms.**
Method: first, alternate forms based on calligraphic traditions are substituted. Then the line length is measured and compared with the target line length, and their difference is determined. Finally, jastyKhatt divides the difference among the alternate glyphs and stretches them. (Manual adjustment of the kashida by the user is also possible; this option is vital for calligraphy-based fonts.)

**Layer 2: Applying the `jalt` table.**
Designers can list swash forms of eligible glyphs in the `jalt` table so that jastyKhatt can substitute them at this stage.

**Layer 3: Adjusting the white space between words (space).**
Finally, if line justification needs further adjustment, jastyKhatt justifies the line by increasing or decreasing the width of the spaces by up to 10%. (This is very useful when the user is manually arranging glyphs.)

### 8.3. Structure of the `jalt`/`from` Table

| Target glyph (final form, after isol/init/medi/fina) | List of alternates |
|---|---|
| e.g. `beh.init.skl` | `[beh.init.skl.alt1]` (usually only one) |
| `kashida-ar` (tatweel) | `[kashida-ar.ss02 ... kashida-ar.ss0N]` (several alternates with different lengths) |

The builder converts this into the `jalt` feature:

```fea
feature jalt {
  script arab;
  lookup jalt_swash {
    lookupflag IgnoreMarks RightToLeft;
    sub beh.init.skl from [beh.init.skl.alt1];
    ...
  } jalt_swash;
  lookup jalt_kashida {
    lookupflag IgnoreMarks RightToLeft;
    sub kashida-ar from [kashida-ar.ss02 kashida-ar.ss03 ...];
  } jalt_kashida;
} jalt;
```

**Note:** The `jalt`/`from` table is suitable for **non-context-dependent** cases (free choice from a list). For context-dependent multi-glyph curved kashidas (which only make sense between specific combinations of letters), the contextual table of section 4 is used, not `jalt`.

### 8.4. Software Support Limitations

FFB currently builds fonts for use in browsers, based on OpenType infrastructure and the HarfBuzz shaping engine, and is not designed for use in offline font editors such as Word and InDesign. This is not possible without coordination with those programs.

---

## 9. Limitations and Open Questions

### 9.1. Behaviour in Layout Software

The author's experience with decomposed fonts in Word and InDesign is mixed (font caching, spacing behaviour) and is still being investigated. Specifically:

- Some layout engines do not treat GSUB-substituted glyphs as the "original glyph" when caching the font.
- Spacing and positioning may not be applied correctly after substitution.
- Search and text selection may point to the skeleton glyph, not the original letter.

### 9.2. Other Scripts

Working hypothesis: the skeleton/mark/anchor idea can help with other scripts that rely heavily on combining marks, such as Syriac or Thaana. Scripts with reordering and conjunct formation, such as Devanagari, Tamil, Myanmar or Sinhala, involve additional machinery that FFB does not address.

### 9.3. Language Coverage

The sample font covers almost all languages of the Arabic script. (All Unicode codes are included, but this requires testing and debugging.)

### 9.4. Validation

The tool has been validated on one font family. Reports from other designers are the real test.

### 9.5. Line Justification

Support for `JSTF` in layout engines is weak. FFB generates a substitute for it, described in section 8 (jastyKhatt). The effectiveness of this substitute in various software has not yet been tested.

---

## 10. Roadmap

**Current version (MVP):**

- GSUB `isol`/`init`/`medi`/`fina`
- GPOS `mark`/`mkmk`/`curs`
- Anchor sync tool
- Simple kerning

**Next version:**

- `calt`/`rclt` (context-dependent alternates)
- Advanced kerning (Contextual Mark Positioning)
- Kerning monitor tool
- The jastyKhatt library

**Future:**

- Support for other scripts (Syriac, Thaana)
- Coordination with Word and InDesign
- Full documentation for the designer community

---

## 11. Appendix: Reference Findings

- **Unicode proposal document 2003** (Kew, Mansour, Davis) — the conceptual basis of skeleton + modifier marks.
- **Sakkal Majalla** (Majalla.ttf) — a real-world example of `jalt` with 222 entries, classic precomposed architecture (not skeletal).
- **Arabic Typesetting** (arabtype.ttf) — a real-world example of `jalt` with 14 entries, most interesting case: tatweel with 3 alternates.
- **Article "On Arabic justification, part 3 – historical models"** (Titus Nemeth, researcher at the University of Reading) — historical evidence for three methods of Arabic justification; recommends reducing the use of flat tatweel and preferring white space and swash/curved kashida.
- **Reference UFO sample:** FFB_Master (Persian) — real skeletal architecture, standard fontTools anchors, and GSUB decompose generated by FontLab, which the builder is meant to reproduce automatically and reliably.
