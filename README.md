# FFB: Font Feature Builder

FFB generates OpenType layout features for Arabic-script fonts by treating a typeface as a set of skeleton glyphs, mark glyphs and anchors instead of pre-composed glyphs.

## What is FFB?

Arabic-script fonts traditionally need a separate glyph for every letter combined with every dot or diacritic. The glyph count explodes and the feature code becomes hard to maintain. FFB has three goals:

1. **Prevent glyph explosion.** Each letter is split into a skeleton glyph and one or more mark glyphs, joined by anchors.
2. **Automate feature generation.** FFB reads the UFO and produces a `.fea` file with the GSUB and GPOS lookups; the font is then compiled with ufo2ft / fontmake.
3. **Provide infrastructure for line justification**, including stretchable alternates that a script such as JustyKhatt can use at the DOM layer.

## How it works

### Skeletal decomposition

The encoded glyph (for example `beh-ar`) stays empty. At runtime GSUB replaces it with a skeleton for the correct positional form and the marks it needs. GPOS then attaches each mark to the skeleton.

<img width="875" height="403" alt="image" src="https://github.com/user-attachments/assets/0297a29a-b9c6-4a05-8dd7-1fe478f65f5d" />

*Figure 1. One letter = skeleton + mark + anchor.*

**Anchor naming:** an anchor without an underscore (`B`) sits on the skeleton; the same name with an underscore (`_B`) sits on the mark. Anchors used:

| Anchor | On skeleton | On mark | Meaning |
|---|---|---|---|
| Top mark | `T` | `_T` | Dot/diacritic above the letter |
| Bottom mark | `B` | `_B` | Dot/diacritic below the letter |
| Ring | `R` | `_R` | Modifier ring above/below |
| Sarkesh | `S` | `_S` | The stroke that turns kaf into gaf |
| Bar | `D` | `_D` | Bar on reh, lam, waw |
| Cursive | `E` | `_E` | Cursive entry/exit |

### Pipeline

<img width="875" height="347" alt="image" src="https://github.com/user-attachments/assets/97bc897d-dce1-41fe-80cb-518499597626" />

*Figure 2. From the font editor to a compiled font.*

| Stage | What happens |
|---|---|
| UFO | Skeletons, marks and anchors drawn in any editor |
| GSUB | `isol` / `init` / `medi` / `fina`, then `calt` / `rclt` / `jalt` / `falt` |
| GPOS | `mark`, `mkmk`, `curs` and `kern` |
| Output | `.fea` file, compiled to TTF/OTF with ufo2ft / fontmake |

### Line justification features

FFB also provides infrastructure for line justification, which is essential for calligraphic styles such as Nastaliq and Shikasteh Nastaliq.

| Feature | Purpose |
|---|---|
| `jalt` | Justification Alternates — general-purpose alternates for justification (e.g. different kashida lengths). |
| `falt` | Final Glyph on Line Alternates — alternate forms designed specifically for line-final glyphs, with shorter or longer tails. In Nastaliq and Shikasteh, this is particularly useful for the line-final yeh (yā-ye barī / yā-ye bargardūn), which can shorten the line by using a more compact form. |

**Note on `falt`:** This feature is applied **last**, after all other features have been applied to the run. HarfBuzz (the shaping engine used by browsers) does not perform line breaking and therefore cannot apply `falt` automatically. JustyKhatt acts as the justification engine that detects line ends and applies `falt` on the final glyph to **reduce line width** when needed.

## Screenshots

_To be added:_

<img width="869" height="464" alt="image" src="https://github.com/user-attachments/assets/5f1bbc53-1073-44bf-b9f1-b45efe3e9bd3" />
<img width="442" height="291" alt="image" src="https://github.com/user-attachments/assets/1f97296e-8fdb-4240-928b-5a6be144cd1e" />

## The FFB Manifesto

- **Fonts should be designed, not hand-coded.** Designers draw glyphs and place anchors; FFB handles the layout logic.
- **Skeletons and marks replace pre-composed glyphs.**
- **Feature code is generated and reproducible from the UFO.**
- **Justification belongs in the font as well as in the layout engine.**
- **Every result is validated and reported, never silently guessed.**

Roadmap items that follow from this:

- Release the JustyKhatt library.
- Release a master font built with FFB.

## Current Status

- **Working:** FFB core for Arabic (`isol`, `init`, `medi`, `fina`, `mark`, `mkmk`).
- **In development:** `calt`, `rclt`, `jalt`, `falt`, and automatic kerning.
- **Design phase:** JustyKhatt, the JavaScript library for kashida-based line justification.

**Limitation:** the justification approach relies on browser shaping (HarfBuzz) and has not been tested on other engines.

## Installation and usage

```bash
git clone https://github.com/AzizMohseny/FFB
cd FFB
pip install -r requirements.txt
```

See the folders `examples`, `sample-font`, `src` and `tools` in the repository.

Project site: [ffb-flame.vercel.app](https://ffb-flame.vercel.app)

## License

FFB is released under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See the `LICENSE` file. Make sure the `LICENSE` file and the repository sidebar both say AGPL-3.0.
