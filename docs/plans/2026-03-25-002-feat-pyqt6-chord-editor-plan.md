---
title: PyQt6 Chord Editor — Two-Column Text-to-Chord GUI
type: feat
status: completed
date: 2026-03-25
origin: docs/brainstorms/2026-03-25-chord-editor-brainstorm.md
---

# PyQt6 Chord Editor — Two-Column Text-to-Chord GUI

## Overview

A minimalist PyQt6 desktop text editor where every Return press classifies the current line through the emotional embedding pipeline, plays the matching chord via Csound, and appends a harmonic annotation in a synchronized right-hand column. The editor is a thin UI shell — no changes to any existing `src/` modules.

## Proposed Solution

New entry point `src/editor.py` wires Qt events to the existing `Classifier` and `CsoundBridge` backend. A new spec `docs/specs/06-editor.md` is written first, per the project constitution.

Layout:
```
┌─────────────────────────────────┬──────────────────────┐
│  I lost myself today            │  vi — A minor  0.72  │
│  The light came back             │  I — C major   0.88  │
│  Grief and gold                 │  ii — D minor  0.61  │
│  ▌                              │                      │
└─────────────────────────────────┴──────────────────────┘
```

## Technical Considerations

### Architecture

- **Entry point:** `src/editor.py` — new file, no modifications to existing src/ modules
- **Spec-first:** write `docs/specs/06-editor.md` before implementing (project constitution)
- **Classifier threading:** single persistent `QThread` worker with an internal queue; all classify calls serialized through it to avoid race conditions from rapid Enter presses
- **Startup:** classifier loads in background QThread; window opens immediately but editor is disabled with a status bar message until load completes
- **Csound:** `CsoundBridge` init wrapped in try/except `CsoundNotAvailableError`; on failure set `bridge = None` and fall back to console-only output (mirrors `main.py` pattern)
- **`sys.path`:** replicate the `sys.path.insert(0, str(Path(__file__).parent))` pattern from `main.py:18` so imports resolve correctly

### Key Behavioral Decisions (from brainstorm)

- **Trigger:** Return key only — no real-time prediction
- **Completed lines:** permanently read-only; no re-submission mechanism (simplest interpretation consistent with brainstorm)
- **Annotation format:** `numeral — chord name  score` e.g. `vi — A minor  0.72`
- **Chord overlap:** new Enter immediately interrupts the previous chord (`CsoundBridge` handles this via `i -1 0 0`)
- **Blank lines:** no-op — pressing Return on an empty line does nothing; cursor stays
- **Low confidence:** no visual distinction — score number communicates confidence (see brainstorm: docs/brainstorms/2026-03-25-chord-editor-brainstorm.md)
- **Pending annotation:** while a line is queued for classification, show `...` placeholder in the right column
- **Line wrap:** disabled in left pane to preserve 1:1 visual alignment with annotation column
- **Auto-scroll:** view always scrolls to keep the current editable line visible after each Return
- **Window close:** `closeEvent` signals worker thread to stop, waits up to 2s, then calls `bridge.close()`

### Export

- **Trigger:** `Cmd+S` / `Ctrl+S` — standard save shortcut
- **Dialog:** native file save dialog; user chooses base name and directory
- **Output:** two files written in one action — `<basename>.json` and `<basename>.txt`
- **JSON schema:** array of objects `{line: str, numeral: str, name: str, score: float, low_confidence: bool}` per submitted line; current unsubmitted line excluded
- **TXT schema:** `<line text>  |  <numeral> — <name>  <score>` per line, newline-separated

### Aesthetic

- Background: `#1a1a1a`, text: `#e0e0e0`, annotation column: `#888888`
- Font: `Menlo, Courier New, monospace` at 13pt
- Minimum window size: 900×500px

## Acceptance Criteria

- [ ] `docs/specs/06-editor.md` written and matches this plan before any code is written
- [ ] `src/editor.py` is a new file; no existing `src/` files are modified
- [ ] Window opens immediately; editor is disabled with status bar "Loading model…" until classifier is ready
- [ ] Classifier load failure shows status bar error message; editor remains disabled (no crash)
- [ ] `CsoundNotAvailableError` on startup silently activates dry-run mode; console prints chord name + score on each classification (mirrors `main.py` behavior)
- [ ] Pressing Return on a non-empty line: classifies, plays chord, appends read-only line, shows annotation, advances cursor to new editable line
- [ ] Pressing Return on an empty line: no-op — no new line, no chord, cursor stays
- [ ] Rapid Return presses: classify calls are serialized through the worker queue; annotations arrive in correct line order; no out-of-order results
- [ ] Pending annotations show `...` in the right column while classification is in flight
- [ ] New Return interrupts the currently playing chord immediately
- [ ] Completed lines are read-only; current (last) line is the only editable line
- [ ] Right column stays vertically aligned 1:1 with left column lines (line wrap disabled)
- [ ] View auto-scrolls to keep the current editable line visible after each submission
- [ ] `Cmd+S` / `Ctrl+S` opens a native save dialog; writes `<basename>.json` and `<basename>.txt`
- [ ] JSON export schema matches spec; TXT export is human-readable
- [ ] `bridge.close()` called in `closeEvent()`; worker thread stopped before close
- [ ] `ChordResult` is passed between layers — never raw strings
- [ ] `--dry-run` flag (or Csound unavailable) produces console output without crashing
- [ ] Console always prints chord name + similarity score (convention from CLAUDE.md)

## Files to Create / Modify

### New files
- `docs/specs/06-editor.md` — atomic spec (intent, inputs, outputs, algorithm, constraints, example)
- `src/editor.py` — PyQt6 application entry point

### No changes to
- `src/chords.py`, `src/classifier.py`, `src/csound_bridge.py`, `src/main.py`, `src/anchor_builder.py`
- `instruments/pad.orc`, `data/`

## Dependencies & Risks

- **PyQt6 not installed:** add to requirements / install instructions; PySide6 is a drop-in alternative (same API, MIT license)
- **Model load time (~5-15s on CPU):** mitigated by background QThread + disabled UI state
- **`atexit` double-call:** `CsoundBridge.close()` is already wrapped in `except Exception: pass`; safe but fragile — acceptable for now, flagged for future hardening
- **Line wrap alignment:** disabling wrap in `QPlainTextEdit` is straightforward; risk is long lines silently truncating visually (acceptable — user sees horizontal scrollbar)

## Sources & References

### Origin
- **Brainstorm:** [docs/brainstorms/2026-03-25-chord-editor-brainstorm.md](../brainstorms/2026-03-25-chord-editor-brainstorm.md)
  Key decisions carried forward: two-column PyQt6 layout; Return-only trigger; dark minimal aesthetic; both .json + .txt export

### Internal References
- `src/chords.py:43-50` — `ChordResult` dataclass
- `src/classifier.py:21-24` — `Classifier.__init__` (expensive, do once)
- `src/classifier.py:27-37` — empty string fast-path returns I low-confidence
- `src/csound_bridge.py:18-27` — `CsoundNotAvailableError`
- `src/csound_bridge.py:44,64-71` — `atexit` registration + `close()`
- `src/main.py:18` — `sys.path` pattern to replicate
- `src/main.py:47-53` — `process()` function pattern: classify → play → print
- `docs/specs/01-05` — existing specs for naming/structure reference
