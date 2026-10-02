# FFB — Font Feature Builder

**Automating OpenType feature generation for complex scripts.**

---

## The Font That Changed History

Without a doubt, Gutenberg's invention was one of the most transformative in human history. But what did Gutenberg actually invent?

Looking closer, what he truly invented was the **font**. The other elements of printing had already existed. In that sense, one could argue that the font changed the course of history.

Even today, in the age of computers and AI, fonts remain the silent servants of these technologies. To grasp this, one need only imagine a world without fonts.

From the 1960s, when keyboards and monitors were added to computers, fonts found a new stage: the screen. Font technologies evolved through various stages, much like other areas of computing, and today we have **Unicode** and **OpenType** — two nearly flawless standards that enable every language to be used on computers.

Among the world's scripts, Arabic is one of the most complex and detailed to turn into a typeface. Fortunately, OpenType has addressed most of its technical challenges, so the tools are largely in place. Yet the number of Arabic fonts remains strikingly low compared to Latin. According to recent Google Fonts data, the ratio is roughly **1 to 31** — only 52 Arabic families against 1,633 Latin families.

But why? Several factors contribute, which we will explore in detail below.

---

## Factors Behind the Slow Growth of Arabic Typefaces

As noted, despite OpenType having resolved nearly all the challenges of Arabic typeface design, Arabic typefaces remain scarce. Many factors are at play; the most important are:

**1. Fragmented efforts across Arabic-script countries.** The Arabic-script region spans many countries. A shared foundation is needed — one that standardizes workflows, education, definitions, and related matters through collective effort.

**2. Absence of specialized academic programs.** There are no established centers or specialized degree programs (at the Master's or PhD level) for Arabic typeface design.

**3. The inherent complexity of Arabic script.** This complexity can be summarized as follows:
   - 3.1. Due to the cursive nature of Arabic, most letters have **four contextual forms**.
   - 3.2. Nearly **one-quarter of the letters** are marks that sit on other letters (diacritics).
   - 3.3. The presence of **numerous dots**.
   - 3.4. **Contextual shaping** — letters change form when adjacent to others (inspired by calligraphic traditions).
   - 3.5. **Multiple baselines** within a single line.

**4. Fragile job security.** Weak copyright protection and insufficient intellectual property laws in most countries of the region.

---

## Flawed Advice to Unicode and OpenType

Unicode released its first code list, **Unicode 1.0.0**, in 1991. In that version, **169 characters** were assigned to the Arabic script.

OpenType was initiated by Microsoft in 1994 under the name **TrueType Open**, with the goal of solving the problems of complex scripts such as Arabic. A year earlier, Unicode had released version 1.1 — likely the basis for Microsoft's work on OpenType. Version 1.0 included a table for Arabic letters, showing that Unicode experts had nearly grasped the actual glyph structure of Arabic script. However, **flawed advice** led Unicode to add a large number of ligatures to this table in version 1.1 — ligatures that were unnecessary. Since then, Unicode's Arabic tables have changed very little.

In 1996, Adobe joined the TrueType Open project, and the name was changed to **OpenType**. The first version, **OpenType 1.0**, was released in 1997.

OpenType was a miracle for Arabic script. It allowed us to turn even complex scripts like **Nastaliq** into fonts.

Microsoft has provided excellent, detailed documentation on all aspects of OpenType. Unfortunately, again due to flawed advice, the sample it provided — **Arabic Typesetting** — uses only **20% of OpenType's capabilities**. The problems of Arabic script in this sample were solved using the **metal-type (ligature) method**, resulting in **glyph explosion**. Of the 2,980 glyphs in this font, **2,480 are Arabic** — whereas, given OpenType's capabilities, this font should have been manageable with around **600 glyphs**.

On the other hand, OpenType's excellent line-justification features — such as `jalt` and `falt` — are not well supported by Word and InDesign.

Of course, Microsoft has no obligation to spend on Arabic script, since its market in the Arabic-script region is weak. It has already done a great deal. In fact, it has provided an excellent infrastructure. It is now the responsibility of the **beneficiaries** of this script to use that infrastructure and develop standard methods and facilitators for producing better and faster Arabic fonts.

---

## Proposed Solution

I began designing fonts before OpenType and Unicode were introduced. For reasons I outlined above, I set this work aside. When I recently decided to redesign those typefaces from the 1980s and 1990s, I encountered OpenType and Unicode — and gradually became familiar with the challenges of designing Arabic script.

Drawing on my background in calligraphy and my analysis of the pen's movement path in writing each letter, I felt I could contribute to solving some of these technical problems. I began by analyzing Arabic letters and dividing them into two main categories: **skeletons** (base letters) and **marks** (diacritics and dots).

In this context, I came across Unicode documents **L2/03-044** and **L2/03-154**, published in 2003, which proposed exactly this approach.

However, Unicode rejected these proposals — not because they were technically wrong, but because the wrong path had already been taken and invested in. Returning to the right path would mean admitting the mistake, and no one was willing to take responsibility for it.

The history of technology is full of examples where the wrong path — not for technical reasons, but due to **sunk costs, stakeholder interests, and fear of reputational damage** — continued. Arabic encoding in Unicode is one such example. The correct technical solution (the **generative model**) was identified in 2003 and proposed by prominent experts such as **Kamal Mansour, Attash Durrani, and Jonathan Kew**. But due to Unicode's structural constraints and the technical conditions of the time, it was not implemented. Today, twenty years later, returning to the correct path within Unicode is impossible.

A mistake, if it continues, becomes a tradition; and a tradition, if it is not criticized, becomes a **false wisdom**. History is full of "false wisdoms" born from mistaken traditions — and those who saw this distinction early were able to build a new path.

---

## The Font Feature Builder (FFB)

After analyzing these issues, I realized this did not mean the solution was impossible — only that it had to be implemented at a **different layer: the font layer**.

Decomposed Arabic fonts had been produced by my colleagues in Iran for years — almost simultaneously with the publication of those Unicode documents — and many fonts have been built this way. However, I have attempted to **document the standard method** for producing them.

The strategy is to create **three layers** in each typeface:

1. **Skeletons**: the base letters.
2. **Marks**: the marks that sit on the skeletons.
3. **Anchors**: the elements that connect marks to skeletons.

Using Unicode tables, I extracted all the parent glyphs across different languages, built the initial **GSUB** table based on skeletons and marks, and defined a set of anchors, placed precisely on both marks and skeletons.

This produced a standard font.

I then built a builder that generates **GPOS tables** (`mark`, `mkmk`, `cursive`) from the UFO output, based on the skeletons, marks, and anchors.

At this point, the **core of FFB** was formed.

The next stages involve building the **alternates system** (calt, rclt, jalt, falt) and, finally, an **automatic kerning system** for the correct positioning of dots and diacritics.

In this way, FFB makes the production of Arabic typefaces significantly easier and faster, enabling designers to generate features without relying on a separate developer.

Based on my investigations, I believe this builder can be applied to **most complex scripts** — because all fonts consist of these same three layers: skeletons, marks, and anchors. This includes scripts such as Devanagari, Tamil, Myanmar, Sinhala, Syriac, Thaana, Thai, and others.

---

## A Path Forward

The problem is not that the correct solution was unknown. The problem is that the wrong path was taken first — and once taken, it became tradition. But tradition, however long it lasts, does not make a solution correct.

FFB is an attempt to build the correct path at a layer where it is still possible: **the font layer**. It does not require Unicode to change. It does not require OpenType to be redesigned. It only requires that we treat Arabic — and every complex script — as what it truly is: **skeletons, marks, and the anchors that connect them.**

If this approach proves useful, it can do more than make Arabic font production faster. It can make it **accessible** — to designers who have the skill but not the engineering background, and to communities whose scripts have been waiting for a standard that fits them.

This is the path I am building. I invite all experts and engineers in the field of typeface design to walk it with me. The path may not yet be complete — but it is no longer empty.

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.
