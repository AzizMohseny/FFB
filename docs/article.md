# The Font Feature Builder (FFB): Treating Arabic Script as Skeletons, Marks and Anchors

*Draft for discussion. Statements that are the author's opinion or estimate are marked as such.*

## 1. Why fonts matter

Gutenberg's press combined several existing techniques. One could argue that its most distinctive contribution was the typeface: a reusable, systematic set of letterforms. Today fonts remain a largely invisible layer under every screen and printed page.

Unicode and OpenType now let almost every written language be used on computers. Arabic script is one of the hardest to turn into a typeface, yet OpenType gives font makers most of the tools they need. Even so, Arabic-script type design remains thinly populated. As reported by Whitecliffe University of Applied Sciences, Google Fonts listed 52 Arabic families against 1,633 Latin families in June 2025, roughly 1 to 31 [1].

## 2. Why Arabic typefaces are comparatively scarce

Many factors contribute. The following are the author's assessment, not the result of a survey:

1. **Fragmented effort.** The Arabic-script world spans many countries and no shared body standardizes workflows, terminology or education.
2. **Few specialized academic programs.** The author is not aware of dedicated postgraduate programs in Arabic type design. (This is an impression; it has not been systematically checked.)
3. **Technical complexity of the script:**
   - most letters have up to four contextual forms (isolated, initial, medial, final);
   - a large share of the marks in the script are dots and diacritics that sit on or under other letters;
   - the number of dots to position is high;
   - letterforms change with their neighbours, following calligraphic tradition;
   - several baselines can coexist in one line.
4. **Weak economics.** Where intellectual-property protection is weak, it is hard to make a living from type design.

## 3. A generative model that was proposed and not adopted

Unicode encodes Arabic letters as complete units. It also contains Arabic Presentation Forms blocks, which exist mainly for compatibility with legacy character sets and are not needed by modern shaping engines.

In 2003 two documents proposed describing Arabic letters generatively, as skeletal base letters plus combining marks:

- J. Kew, *Encoding Arabic extensions: options for the future of Unicode*, February 2003 [2];
- J. Kew, K. Mansour, M. Davis, *Proposal to encode productive Arabic-script modifier marks*, May 2003 [3]. It proposed 22 combining marks (dot patterns, small V, inverted V, ring, tah, bar) and one dotless base letter.

The Unicode Technical Committee did not adopt the approach. In a 2006 letter, Kew explains why: the benefit did not justify the cost of a change at that stage, normalization stability prevents giving existing letters new decompositions, and two ways to encode the same letter would create ambiguity and spoofing problems; he also states that many experts would have preferred the generative model [4]. The author of this article agrees with the technical idea of those proposals but accepts that the reasons given are real engineering constraints.

The consequence is that the generative model cannot live in the character encoding. It can still live in the font.

## 4. The font layer

Decomposed Arabic fonts are not new. Type designers in Iran, among others, have built fonts this way for years, but the method has not been documented as a reusable standard. FFB is an attempt to document it and to automate its repetitive parts.

The method divides a typeface into three layers:

1. **Skeletons**: dotless base shapes, one per joining form.
2. **Marks**: dots, diacritics and other marks, drawn once each.
3. **Anchors**: named points on skeletons and marks that say where a mark attaches.

An encoded letter such as BEH is a *glyph with an empty outline*. At run time, GSUB replaces it with a skeleton plus a mark (for example `behDotless.init.skl` + `dotbelow.mrk.skl`). GPOS then places the mark using the anchors. Because dots are marks, the glyph count does not multiply with every dot-bearing letter.

By way of contrast, in the author's own count, Arabic Typesetting (Windows 10, October 2025) contains 2,980 glyphs, 2,480 of them Arabic [5]. The author's estimate is that a decomposed design could cover the same repertoire with a few hundred glyphs, but this has not been demonstrated on that font. FFB's sample font (519 glyphs including Latin) is a small data point, not a proof.

## 5. What FFB does today

FFB reads a UFO source and generates feature code:

| Output | Status |
|---|---|
| GSUB `isol`, `init`, `medi`, `fina` decomposition (from a table of letter → skeleton + marks) | working |
| GPOS `mark` (mark-to-base) and `mkmk` (mark-to-mark) from anchors | working |
| GPOS `curs` (cursive attachment) from `Ex`/`_Ex` anchors | working |
| Synchronizing anchor coordinates in an existing feature file with the UFO | working (browser tool) |
| Simple hand-written `kern` for non-joining letters | template only |
| Contextual alternates (`calt`, `rclt`) | planned |
| Automatic kerning and contextual mark shifts | planned |

FFB depends on a naming convention (anchor names `Tm`, `Bm`, `ring`, `sarkesh`, `bar`, `Ex` and their `_` counterparts; `.skl` and `.mrk` glyph suffixes). It is not font-agnostic. Any font that follows the convention can use it, and the convention is documented in the user guide.

## 6. Limits and open questions

- **Behaviour in layout software.** The author's experience with decomposed fonts in Word and InDesign is mixed (font caching, spacing behaviour) and is still being investigated.
- **Other scripts.** The author's hypothesis is that the skeleton/mark/anchor idea can help with other scripts that rely heavily on combining marks, such as Syriac or Thaana. Scripts with reordering and conjunct formation, such as Devanagari, Tamil, Myanmar or Sinhala, involve additional machinery (reordering, conjuncts) that FFB does not address. No work has been done on them.
- **Language coverage.** The sample font covers Persian; Kurdish, Urdu, Pashto and Uyghur letters are planned.
- **Validation.** The tool has been validated on one font family. Reports from other designers are the real test.

## 7. Invitation

FFB is open source and intended for type designers who have the skill but not an engineering background. The aim is to turn the skeleton/mark/anchor method into something documented and shareable. Designers, engineers and users of Arabic-script type are invited to try it, report problems and extend it.

## References

1. Whitecliffe University of Applied Sciences, "Typography is never neutral", 18 August 2025. https://whitecliffe.de/en/news/typography-is-never-neutral/ (reports 52 Arabic and 1,633 Latin families on Google Fonts, June 2025).
2. J. Kew, "Encoding Arabic extensions: options for the future of Unicode", Unicode L2/03-044, 11 February 2003. https://www.unicode.org/L2/L2003/03044-arabic-ext-opt2.pdf
3. J. Kew, K. Mansour, M. Davis, "Proposal to encode productive Arabic-script modifier marks", Unicode L2/03-154, 16 May 2003. https://www.unicode.org/L2/L2003/03154-gen-arabic-prop.pdf
4. J. Kew, letter to the Unicode Technical Committee on the preliminary proposal to add nuqta characters to the Arabic block (L2/06-240), 19 July 2006. https://www.unicode.org/L2/L2006/06240-durrani.pdf
5. Author's own count of glyphs in the Arabic Typesetting font shipped with Windows 10 (October 2025), made with FontLab.
