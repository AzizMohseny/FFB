# JustyKhatt Engine Architecture

**Script-Agnostic DOM-Level Line Justification Engine**

## 1. Scope and Purpose
JustyKhatt is a DOM-level line justification engine designed for complex writing systems. It provides a generic processing pipeline in which script-specific and style-specific justification rules are supplied through independent **Rule Packs**.

The architecture is intentionally **script-agnostic**. Support for a new writing system or typographic style should be added primarily by creating a new Pack, without modifying the Core processing modules.

In formal and administrative text, **legibility is the primary objective**. Normal mode therefore favors controlled and proportional distribution of available space. Artistic mode is an optional strategy that may apply stronger calligraphic preferences, while remaining independent from the Core engine.

## 2. Architectural Principles

| Principle | Meaning |
|---|---|
| **Core / Pack separation** | Generic processing belongs to Core; calligraphic decisions belong to Rule Packs. |
| **Script agnosticism** | The Core must not contain rules specific to Arabic, Latin, Devanagari, or another script. |
| **Data-driven tagging** | Character eligibility and font-specific capabilities are described by configuration data rather than hard-coded decisions in the tagger. |
| **Pack-owned decisions** | A Rule Pack determines which eligible opportunities are used and by how much. |
| **Renderer as executor** | The renderer applies commands; it does not decide what should be stretched or substituted. |
| **Mode independence** | Normal and Artistic are strategies selected by the router, not separate versions of the Core. |
| **Font-aware behavior** | A Pack may use the capabilities and axes of the active font when producing commands. |
| **No direct DOM manipulation by Packs** | A Rule Pack must return a Command List (data) to the Renderer. It must not touch the DOM directly. |

## 3. Directory Structure

```text
JustyKhatt/
├── index.html
├── style.css
├── ARCHITECTURE.md
│
├── core/
│   ├── config.js          (Core-level generic settings)
│   ├── lineAnalyzer.js    (Detects lines and word boundaries from DOM)
│   ├── measure.js         (Calculates remaining space)
│   ├── tagger.js          (Identifies stretch/substitution opportunities)
│   ├── renderer.js        (Applies commands to DOM)
│   └── runtime.js         (Debounce and ResizeObserver)
│
└── packs/
    ├── arabic/
    │   └── base/
    │       ├── config.js   (Pack-specific config, char-to-skeleton maps)
    │       ├── kit.js      (Helper functions for Arabic, e.g., distribute, lineWidths)
    │       ├── ffb-caps.js (Extracted font capabilities: stretch/swash data)
    │       ├── normal.js   (Normal justification strategy)
    │       └── artistic.js (Artistic justification strategy)
    │
    ├── latin/
    │   └── gothic/
    │       ├── normal.js
    │       └── artistic.js
    │
    └── indic/
        └── devanagari/
            ├── normal.js
            └── artistic.js
