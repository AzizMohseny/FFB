The Font Feature Builder (FFB)

Treating Arabic Script as Skeletons, Marks and Anchors

Project article  •  Draft for discussion

Core principle  The font provides typographic resources; HarfBuzz shapes the text; JustyKatt makes line-justification decisions.

Abstract

Arabic script is one of the most complex writing systems to turn into a typeface. Despite Unicode and OpenType support, the number of Arabic-script font families remains small compared with Latin. This article introduces the Font Feature Builder (FFB), a generative approach that organizes a font into three layers—skeletons, marks and anchors—and uses that structure to generate OpenType tables. It also describes how those font resources can support a fourth concern: Arabic line justification. FFB operates in the font-production layer; it does not change character encoding and complements Unicode and OpenType. The accompanying JavaScript library, JustyKatt, treats justification as the responsibility of the text-layout layer rather than the font itself.

1. Why fonts matter

Gutenberg’s principal invention was the font: a reusable, systematic set of letterforms. Today, fonts remain a largely invisible layer beneath every screen and printed page.

Unicode and OpenType allow almost every written language to be used on computers. Arabic script remains particularly challenging to turn into a typeface, even though OpenType provides font makers with many of the necessary tools. Arabic-script type design is still comparatively underrepresented. Whitecliffe University of Applied Sciences reported that Google Fonts listed 52 Arabic families against 1,633 Latin families in June 2025—roughly a ratio of 1 to 31 [1].

2. Why Arabic typefaces are comparatively scarce

The following factors are based on the author’s field observations. They are presented as working hypotheses, not as the results of a systematic survey.

Fragmented effort. The Arabic-script world spans many countries, and no shared body standardizes workflows, terminology or education.

Few specialized academic programs. As far as the author is aware, dedicated postgraduate programs in Arabic type design are rare or nonexistent. This impression has not been systematically checked.

Technical complexity of the script.

Most letters have up to four contextual forms: isolated, initial, medial and final.

Many marks are dots and diacritics placed above or below letters.

The number and arrangement of dots create substantial positioning work.

Letterforms change according to their neighbours and calligraphic tradition.

Several baselines can coexist within a single line.

Weak economics. Where intellectual-property protection is weak, it can be difficult to make a living from type design.

3. A generative model proposed but not adopted for encoding

Unicode encodes Arabic letters as complete units. It also contains Arabic Presentation Forms blocks, which exist mainly for compatibility with legacy character sets and are not needed by modern shaping engines for ordinary text.

In 2003, two documents proposed describing Arabic letters generatively, as skeletal base letters plus combining marks:

J. Kew, *Encoding Arabic extensions: options for the future of Unicode*, February 2003 [2].

J. Kew, K. Mansour and M. Davis, *Proposal to encode productive Arabic-script modifier marks*, May 2003 [3]. The proposal included 22 combining marks—dot patterns, small V, inverted V, ring, tah and bar—and one dotless base letter.

The Unicode Technical Committee did not adopt this approach. In a 2006 letter, Kew explained that the benefits did not justify the cost of a change at that stage; normalization stability prevented assigning new decompositions to existing letters; and two ways to encode the same letter could create ambiguity and spoofing risks [4]. He also noted that many experts would have preferred the generative model. This article agrees with the technical idea while recognizing the engineering constraints.

The consequence is that this generative model cannot be introduced into character encoding in the proposed way. It can, however, be implemented at the font-production layer.

4. The font layer

Decomposed Arabic fonts are not new. Type designers in Iran, among others, have used such methods for years, but the workflow has not been documented as a reusable standard. FFB aims to document the method and automate repetitive production tasks.

The method divides a typeface into three layers:

4.1 Skeletons

Skeletons are dotless base shapes, typically one per joining form. The naming convention is <letter>.<form>.skl, for example beh.init.skl. A letter with four joining forms may need up to four skeletons. Skeletons can also use additional axes in a variable font. Decomposition can continue into smaller components—for example, decomposing hah-ar.init into hahHead plus a kashida component—which can be useful in calligraphic type design.

4.2 Marks

Marks are dots, diacritics and other small components, drawn once and reused. The naming convention is <name>.<position>.mrk, for example dotbelow.mrk.skl. A mark can be placed on many skeletons without being duplicated.

4.3 Anchors

Anchors are named points on skeletons and marks that define attachment positions. The convention used by this project includes Tm (top-middle), Bm (bottom-middle), ring, sarkesh, bar, Ex and their underscore-prefixed counterparts.

An encoded letter such as BEH can be represented by a glyph with an empty outline. At shaping time, GSUB replaces it with a skeleton plus a mark—for example, behDotless.init.skl plus dotbelow.mrk.skl. GPOS then positions the mark using anchors.

Because dots and diacritics are reusable marks, the glyph inventory does not need to multiply for every letter that carries them: one skeleton plus one mark glyph can cover every letter that shares those components. A quantitative comparison with conventional fonts is deferred until the full set of contextual alternates has been designed.

4.4 Kashida and line justification

Arabic line justification is not simply a matter of stretching spaces between words. JustyKatt follows a separation-of-responsibilities principle: the font supplies typographic resources, HarfBuzz performs shaping, and the justification engine decides how to use those resources.

The principal mechanisms available to a justifier are:

Variable alternate forms. Select a suitable alternate and adjust its width through a variable-font axis. This is the first-priority mechanism in the current JustyKatt design.

Fixed alternate forms. Use calligraphic alternates that change the shape without continuously varying an axis—for example, a broken yeh or a toothless seen.

Word-space adjustment. As a final, limited correction, slightly compress word spacing. The current design considers a small negative adjustment, with approximately −10% as an example ceiling rather than a universal rule.

Kashida (tatweel) traditionally elongates connected letters without increasing the spaces between words. It is appropriate only where the letter connection and design permit it. In FFB’s decomposed structure, elongation can be applied to the skeleton while marks remain separate, which may help preserve their independent positioning.

Possible implementation techniques include:

Decomposing a character into a head component and an elongation component, then replacing the latter with wider alternatives or controlling it through a variable-font axis.

Defining attachment points that specify where elongation begins and where the following skeleton resumes.

Using GSUB substitutions to select suitable components or alternates.

Using curs to attach connected components.

Using mark and mkmk to maintain dot and diacritic placement as forms change.

OpenType defines a JSTF table for justification-related behaviour. Support for it is limited or inconsistent across layout engines, so JustyKatt is designed to make justification decisions outside the font rather than depend on JSTF support. The actual set of usable features will depend on the font, shaping engine and host environment.

The JustyKatt manifesto

Line justification is not the font’s job; it is the text engine’s job.

The font provides typographic resources. HarfBuzz shapes the text. JustyKatt measures, evaluates and chooses how to use the available resources.

The manifesto has three practical consequences:

Fonts provide capacity. They supply alternate forms, controlled variability and the information needed to preserve calligraphic structure.

The justifier makes decisions. It measures line length, evaluates the font’s capabilities and chooses the location, type and amount of elongation.

Beauty comes before mechanical correction. The system first uses calligraphic options, then applies restrained spacing adjustments if necessary.

5. What FFB does today

FFB reads a UFO source and generates OpenType feature code. The current status is summarized below.

Output / capability

Status

GSUB decomposition: `isol`, `init`, `medi`, `fina` from letter-to-skeleton/mark mappings

Working

GPOS `mark` and `mkmk` from anchors

Working

GPOS `curs` from `Ex` / `_Ex` anchors

Working

Synchronizing anchor coordinates in an existing feature file with UFO anchors (browser tool)

Working

Simple hand-written `kern` for non-joining letters

Template only

Contextual alternates (`calt`, `rclt`) 

Planned

Automatic kerning and contextual mark shifts

Planned

Kashida resources and justification integration

Planned

FFB depends on a naming convention: anchor names such as Tm, Bm, ring, sarkesh, bar, Ex and their underscore-prefixed counterparts, plus .skl and .mrk glyph suffixes. It is not font-agnostic at the source level. A font that follows the convention can use the tool; the convention is documented in the user guide.

6. Limits and open questions

6.1 Behaviour in layout software

The author’s experience with decomposed fonts in Word and InDesign is mixed, particularly around font caching and spacing behaviour. Issues under investigation include:

Some layout engines may not treat GSUB-substituted glyphs as the original glyph when caching font data.

Spacing and positioning may not be applied as expected after substitution.

Search and text selection may refer to a skeleton glyph rather than the original encoded character.

6.2 Other scripts

The author’s working hypothesis is that the skeleton/mark/anchor model may also help scripts that rely heavily on combining marks, such as Syriac or Thaana. Scripts with reordering and conjunct formation—including Devanagari, Tamil, Myanmar and Sinhala—require additional mechanisms that FFB does not currently address. No implementation work has been done for these scripts.

6.3 Language coverage

The sample font is intended to cover nearly all languages written in Arabic script. Although the glyph inventory aims to include all Unicode-defined glyphs relevant to the project, practical coverage still requires testing.

6.4 Validation

The tool has been validated on one font family. Reports and tests from other designers will be an important measure of its generality.

6.5 Line justification

Justification behaviour depends on the font’s resources, HarfBuzz shaping behaviour, and the host rendering environment. The proposed workflow and its effectiveness across browsers and desktop layout applications still require systematic testing.

7. Invitation

FFB is open source and intended for type designers who have the skill but may not have an engineering background. Its goal is to make the skeleton/mark/anchor workflow documented, repeatable and shareable. Designers, engineers and users of Arabic-script type are invited to try it, report issues and extend it.

References

1. Whitecliffe University of Applied Sciences, “Typography is never neutral,” 18 August 2025. Reports 52 Arabic and 1,633 Latin families on Google Fonts in June 2025. Source

2. J. Kew, “Encoding Arabic extensions: options for the future of Unicode,” Unicode L2/03-044, 11 February 2003. Source

3. J. Kew, K. Mansour and M. Davis, “Proposal to encode productive Arabic-script modifier marks,” Unicode L2/03-154, 16 May 2003. Source

4. J. Kew, letter to the Unicode Technical Committee on the preliminary proposal to add nuqta characters to the Arabic block (L2/06-240), 19 July 2006. Source
