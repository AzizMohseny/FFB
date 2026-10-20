# JustyKhatt Engine Architecture

**Script-Agnostic DOM-Level Line Justification Engine**

---

## 1. Scope and Purpose

JustyKhatt is a DOM-level line justification engine designed for complex writing systems. It provides a generic processing pipeline in which script-specific and style-specific justification rules are supplied through independent **Rule Packs**.

The architecture is intentionally **script-agnostic**. Support for a new writing system or typographic style should be added primarily by creating a new Pack, without modifying the Core processing modules.

In formal and administrative text, **legibility is the primary objective**. Normal mode therefore favors controlled and proportional distribution of available space. Artistic mode is an optional strategy that may apply stronger calligraphic preferences, while remaining independent from the Core engine.

---

## 2. Architectural Principles

| Principle | Meaning |
|---|---|
| **Core / Pack separation** | Generic processing belongs to Core; calligraphic decisions belong to Rule Packs. |
| **Script agnosticism** | The Core must not contain rules specific to Arabic, Latin, Devanagari, or another script. |
| **Data-driven tagging** | Character eligibility is described by configuration data rather than hard-coded decisions in the tagger. |
| **Pack-owned decisions** | A Rule Pack determines which eligible opportunities are used and by how much. |
| **Renderer as executor** | The renderer applies commands; it does not decide what should be stretched or substituted. |
| **Mode independence** | Normal and Artistic are strategies selected by the router, not separate versions of the Core. |
| **Font-aware behavior** | A Pack may use the capabilities and axes of the active font when producing commands. |

---

## 3. Directory Structure

The following structure is illustrative. Arabic/Naskh is shown **only as an example** of how a script and style can be packaged; it is not a special architectural dependency.

```text
JustyKhatt/
├── index.html
├── style.css
├── ARCHITECTURE.md
│
├── core/
│   ├── config.js
│   ├── tagger.js
│   ├── measure.js
│   ├── renderer.js
│   └── engine.js
│
└── packs/
    ├── arabic/                 ← Example script pack
    │   ├── base/
    │   ├── naskh/
    │   │   ├── normal.js
    │   │   └── artistic.js
    │   ├── nastaliq/
    │   │   ├── normal.js
    │   │   └── artistic.js
    │   └── kufi/
    │       ├── normal.js
    │       └── artistic.js
    │
    ├── latin/                  ← Example script family
    │   └── gothic/
    │       ├── normal.js
    │       └── artistic.js
    │
    └── indic/                  ← Example script family
        └── devanagari/
            ├── normal.js
            └── artistic.js
```

The examples above are placeholders demonstrating the extensibility model. A real implementation may organize Packs differently as long as the Core-to-Pack contract remains intact.

---

## 4. Core Modules

### 4.1 `config.js` — Data Source

Contains shared configuration data used by the Core, including character-to-skeleton mappings and lists of characters or skeletons associated with stretch groups such as `vL`, `vR`, `vB`, and `sw`.

It contains **data rather than justification algorithms**. The exact data model may evolve with the supported fonts and scripts.

### 4.2 `measure.js` — Measurement Engine

Parses the input text into words or segments and measures their rendered width through the DOM.

Inter-word spacing is included in the measurement.

The module reports:

- word count
- calculated width
- difference between measured width and target line width

It does **not** decide how the remaining space should be distributed.

### 4.3 `tagger.js` — Tagging Module

Evaluates characters against configuration data and identifies eligible stretch or substitution opportunities.

It produces structured tagging information for the active Rule Pack.

It does **not**:

- perform line justification mathematics
- decide the final stretch amount
- choose the final set of stretch operations

Those decisions belong to the active Rule Pack.

### 4.4 `engine.js` — Manager / Router

Coordinates the pipeline and selects the appropriate Rule Pack according to:

- active script/style
- font capabilities
- selected mode

It is responsible for routing, not for implementing script-specific calligraphic rules.

### 4.5 `renderer.js` — Render / Execution Module

Receives final commands from a Rule Pack and applies them to the DOM.

For fonts that expose variable axes, commands may be translated into `font-variation-settings`. Other commands may request glyph or feature substitutions.

The Renderer **executes commands**. It does not make calligraphic decisions.

---

## 5. Rule Packs

Rule Packs contain the script- and style-specific logic that determines how a justified line should be constructed.

A Rule Pack is the primary extension point of JustyKhatt.

### 5.1 Normal Mode

Normal mode prioritizes **legibility and controlled distribution** of available space.

A typical strategy may distribute stretch proportionally among suitable opportunities, subject to the capabilities and limits of the active font.

### 5.2 Artistic Mode

Artistic mode is an optional **aesthetic strategy**.

It may enforce limits on the number, location, or combination of stretches and substitutions in order to produce a preferred calligraphic appearance.

It remains independent from the Core.

---

## 6. Rule Pack Contract

A Rule Pack receives structured information from the Core and returns executable justification commands.

### Input to a Rule Pack

- Measured line/word data
- Target line width and remaining space
- Tagged stretch/substitution candidates
- Active script/style and mode
- Relevant font capabilities and axis information
- Pack-specific options or limits

### Output from a Rule Pack

- Selected stretch opportunities
- Per-opportunity stretch values
- Variable-font axis commands where applicable
- Glyph/feature substitution commands where applicable
- Any additional Renderer-executable instructions

This contract is the boundary between the generic Core and script/style-specific typography.

---

## 7. Execution Workflow

1. The user enters or supplies text and selects the target width and justification mode.
2. `measure.js` measures the rendered content and calculates the available/remaining space.
3. `tagger.js` identifies characters or glyph positions that are eligible for script-defined operations.
4. `engine.js` resolves the appropriate Rule Pack from the active script/style and mode.
5. The Rule Pack analyzes the available candidates and determines the final justification strategy.
6. The Rule Pack returns Renderer-executable commands.
7. `renderer.js` applies those commands to the DOM.
8. The browser renders the resulting line using the active font and its OpenType/Variable Font capabilities.

---

## 8. Core Processing Flow

```text
┌───────────────────────────────┐
│          User / UI            │
│ text • width • mode • font    │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│          measure.js           │
│ rendered width • remainder    │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│           tagger.js           │
│ stretch / substitution        │
│ candidates                    │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│           engine.js           │
│       Pack / Mode Router      │
└───────────────┬───────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌───────────────┐  ┌───────────────┐
│ normal.js     │  │ artistic.js   │
│ legibility    │  │ aesthetics    │
└───────┬───────┘  └───────┬───────┘
        └────────┬──────────┘
                 ▼
        ┌───────────────────┐
        │    renderer.js    │
        │ execute commands  │
        └─────────┬─────────┘
                  ▼
        ┌───────────────────┐
        │       DOM         │
        │ final rendered    │
        │ justified line    │
        └───────────────────┘
```

---

## 9. Extensibility

Adding support for a new script, writing system, or typographic style should not require changes to the generic Core.

The developer creates a new Pack and implements the Rule Pack contract for that script/style.

For example:

```text
packs/
└── new-script/
    └── new-style/
        ├── normal.js
        └── artistic.js
```

The Pack may use whatever script-specific knowledge is required, including:

- character behavior
- skeleton categories
- preferred stretch locations
- substitution strategies
- variable-font axes
- limits
- aesthetic rules

These decisions remain outside the Core.

---

## 10. Examples and Non-Goals

Arabic, Naskh, Nastaliq, and Kufi are examples of possible Packs, **not architectural assumptions**.

Likewise, Latin/Gothic and Devanagari are examples of other possible implementations.

The Core must not contain special-case branches such as:

```text
if Arabic then ...
if Naskh then ...
if Devanagari then ...
```

Such behavior belongs in the corresponding Pack.

---

## 11. Design Rationale

This separation allows JustyKhatt to evolve from a font-specific justification experiment into a reusable engine architecture.

The Core remains stable while individual Packs can evolve with:

- new fonts
- new OpenType features
- new variable axes
- different calligraphic strategies

The architecture also permits the same text-processing pipeline to support different philosophies of justification. A conservative, legibility-oriented strategy and a more expressive, artistic strategy can coexist without duplicating the Core.

---

## 12. Summary

The central architectural rule of JustyKhatt is:

> **The Core knows how to process. The Rule Pack knows how to justify.**

This separation keeps the engine reusable, makes typography-specific logic replaceable, and allows new scripts and styles to be added without modifying the generic processing pipeline.
