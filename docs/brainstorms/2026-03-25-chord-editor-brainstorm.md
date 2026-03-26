# Brainstorm: Chord Editor

**Date:** 2026-03-25
**Status:** Draft

---

## What We're Building

A minimalist, beautiful desktop text editor (PyQt6) where every time the user presses Return, the current line is classified via the emotional embedding pipeline, the matching chord is played through Csound, and the chord annotation appears in a right-hand column aligned to that line.

The experience: write freely, press Enter, hear the chord. The left side stays clean prose; the right side accumulates a harmonic record of what you wrote.

---

## Core Interaction Model

1. User types a line of text in the left editor pane
2. User presses **Return**
3. The classifier runs on that line → `ChordResult`
4. Csound plays the chord
5. The chord annotation appears in the right column, aligned to the same line
6. Cursor advances to the next empty line

---

## Layout

```
┌─────────────────────────────────┬──────────────────────┐
│  I lost myself today            │  vi — A minor  0.72  │
│  The light came back             │  I — C major   0.88  │
│  Grief and gold                 │  ii — D minor  0.61  │
│  ▌                              │                      │
└─────────────────────────────────┴──────────────────────┘
```

- Left: `QPlainTextEdit` — read-only for completed lines, writable only on the current (last) line
- Right: synchronized chord column — one entry per submitted line, aligned by line number
- Chord entry format: `numeral — chord name  score`  (e.g. `vi — A minor  0.72`)

---

## Why This Approach

- **Two-column over inline annotation:** Text stays uncluttered. The chord column is metadata, not content. More legible for both writing and reviewing.
- **PyQt6 over Tkinter:** Richer stylesheet support enables the minimalist aesthetic — dark background, elegant typography, dimmed chord annotations.
- **Reuses existing pipeline wholesale:** `Classifier` and `CsoundBridge` are unchanged. The editor is a thin UI shell around the existing backend.
- **No new architectural concepts:** Just a new entry point (`src/editor.py`) that wires Qt events to existing src/ modules.

---

## Key Decisions

- **Toolkit:** PyQt6 (or PySide6 — same API, MIT license)
- **Aesthetic:** Dark, minimal — think a composer's notebook. Monospace font for text; lighter, smaller font for chord annotations.
- **Chord column detail:** Full `[numeral — name  score]` per line — all three fields as originally desired
- **Persistence:** Save everything — export both the raw text and the chord annotations. Format TBD at planning (JSON or structured .txt)
- **Spec compliance:** A new spec `docs/specs/editor.md` will be written before implementation, per project constitution

---

## Resolved Questions

- **Chord column sync:** Update in place — if a line is re-submitted, its annotation is replaced. Column stays 1:1 with lines.
- **Low confidence handling:** No visual distinction — the score number already communicates confidence.
- **Save format:** Both — export a `.json` (structured, each line paired with its ChordResult) and a `.txt` (human-readable, line + annotation).
- **Chord overlap:** Cut off — new Enter immediately stops the current chord and plays the new one. Responsive, no lag.

## Open Questions

None — all questions resolved.

---

## Out of Scope (for now)

- Real-time chord prediction as-you-type (only on Enter)
- Multiple simultaneous editors or tabs
- Chord playback controls (stop, replay)
- Any change to the classifier, embeddings, or Csound orchestra
