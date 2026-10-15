# FFB (Font Feature Builder)

**Building a standard infrastructure for line justification in complex scripts, based on OpenType**

---

## What is FFB?

FFB is a new definition of non-Latin fonts with complex scripts that pursues several goals:

**1. Preventing glyph explosion**
By using a decomposed approach across three layers: **skeletons**, **marks**, and **anchors**. The role of anchors is to connect skeletons and marks.

**2. Automating font feature generation**
Without dependence on any specific software or platform, using UFO files. Designers prepare their font in any platform they prefer and set the anchors. They then export a UFO file and submit it to FFB, which returns the font's features in a `.fea` file. This dramatically reduces the long and error-prone font production process and prepares the font with very high accuracy.

**3. Building infrastructure for line justification**
One of the most persistent problems in OpenType is line justification in Arabic script. The `jalt` feature and the `JSTF` table were attempts in OpenType to define this at the font layer — but neither succeeded. The `ar-justify` library is another attempt to organize this at the text editor layer. But FFB has its own manifesto for this:

## The FFB Manifesto

**Justification is not the font's job. It is the text engine's job.**

**1. The Font's Responsibility: Providing Capacity**
The font must provide alternate forms, controlled variation of forms, and the facilities needed to preserve the beauty and rules of calligraphy.

**2. The Justifier's Responsibility: Intelligent Decision-Making**
The text engine must measure line length, evaluate the font's capacities, and decide on the location, type, and amount of change in the glyph.

**3. Beauty Over Mechanical Solutions**
Line justification should not be achieved merely by increasing word spacing. Instead, it must adjust elongation according to calligraphic traditions and inject appropriate alternates into the line; then, if necessary, spacing should be adjusted within strict limits.

**4. Releasing the JustyKhatt Library**
Releasing an open-source JavaScript library called JustyKhatt that organizes text justification at the DOM layer for browsers.

**5. Releasing a Master Font**
Releasing a master font that demonstrates the full capacities of a font for justification.

## Current Status

- **FFB:** The core architecture works for Arabic. Anchor synchronization, GSUB, and GPOS (mark, mkmk, cursive) are functional. Alternates (calt, rclt, jalt, falt) and automatic kerning are in development.
- **JustyKhatt:** In the design phase.

## License

AGPL-3.0
