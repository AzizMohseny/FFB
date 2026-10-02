# FFB — Font Feature Builder

**Automating OpenType feature generation for complex scripts.**

FFB treats every font as three layers — skeletons, marks, and anchors — and generates OpenType features automatically from this structure.

## Why This Matters

Despite OpenType solving nearly all technical challenges of Arabic script, the number of Arabic typefaces remains strikingly low — roughly 1 to 31 compared to Latin. The reason is not technical. It is historical.

📄 **[Read the full paper →](PAPER.md)**

## Status

- ✅ Anchor synchronization — functional
- ✅ GSUB generation — functional
- ✅ GPOS generation (mark, mkmk, cursive) — functional
- 🔄 Alternates system (calt, rclt, jalt, falt) — in development
- 🔄 Automatic kerning for dots and diacritics — in development

## Live Tool

🔗 **[Try Anchor Sync →](https://ffb.vercel.app)**

## License

AGPL-3.0
