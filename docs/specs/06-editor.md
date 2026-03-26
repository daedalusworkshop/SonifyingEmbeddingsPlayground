# Spec 06: Chord Editor GUI

## Intent
Provide a minimalist PyQt6 desktop text editor where each Return press classifies the current line, plays the matching chord, and appends a harmonic annotation in a synchronized right-hand column. The editor is a thin UI shell around the existing Classifier and CsoundBridge — no existing modules are modified.

## Inputs
- Keyboard input from the user (text + Return key)
- Optional `--dry-run` flag (skip audio, print results to console)

## Outputs
- Two-column GUI: left pane (editable text), right pane (chord annotations per submitted line)
- Audio via CsoundBridge on each Return (unless dry-run or Csound unavailable)
- Console output per classification: chord name, numeral, score (same as main.py)
- Export on Cmd+S / Ctrl+S: `<basename>.json` and `<basename>.txt`

## Algorithm

### Startup
1. Parse `--dry-run` argument
2. Open the window immediately (left pane disabled, status bar: "Loading model…")
3. Launch background `QThread` worker (`ClassifierWorker`):
   - Calls `Classifier()` once (loads model + anchors)
   - On success: emits `ready` signal → enables left pane, clears status bar
   - On failure: emits `error(msg)` signal → status bar shows error, left pane stays disabled
4. Attempt `CsoundBridge()` in the main thread after classifier is ready (or at startup if fast enough):
   - On `CsoundNotAvailableError`: set `bridge = None`, activate dry-run mode silently

### Per-Return Interaction
1. User presses Return in the editable (bottom) line
2. If the line is empty or whitespace-only: no-op, cursor stays, nothing happens
3. Otherwise:
   a. Freeze the submitted line (read-only)
   b. Append `...` placeholder to the right annotation column at the corresponding line index
   c. Enqueue `(line_index, text)` in the `ClassifierWorker`'s internal queue
   d. Append a new blank editable line; move cursor there
   e. Auto-scroll so the new editable line is visible
4. Worker dequeues and calls `Classifier.classify(text)` → `ChordResult`
5. Worker emits `result(line_index, ChordResult)` signal
6. Main thread receives signal:
   a. Replace `...` with `numeral — name  score` (e.g. `vi — A minor  0.72`) in right column
   b. Call `bridge.play_chord(result)` (or dry-run print)
   c. Print chord name + score to console

### Export (Cmd+S / Ctrl+S)
1. Open native file save dialog (no default path, user chooses base name and directory)
2. Write `<basename>.json`: JSON array, one object per submitted line:
   `{"line": str, "numeral": str, "name": str, "score": float, "low_confidence": bool}`
   (Lines with pending `...` annotations are included with `numeral: null, name: null, score: null, low_confidence: null`)
3. Write `<basename>.txt`: one line per entry:
   `<line text>  |  <numeral> — <name>  <score>`

### Shutdown
1. `closeEvent` signals worker to stop; waits up to 2s for thread to finish
2. Calls `bridge.close()` if bridge is not None
3. Window closes

## Layout
```
┌─────────────────────────────────┬──────────────────────┐
│  I lost myself today            │  vi — A minor  0.72  │
│  The light came back             │  I — C major   0.88  │
│  Grief and gold                 │  ii — D minor  0.61  │
│  ▌                              │                      │
└─────────────────────────────────┴──────────────────────┘
```
- Left: `QPlainTextEdit` — line wrap off; completed lines read-only (achieved via a custom key filter); only the last line is editable
- Right: `QListWidget` — one item per submitted line; items not selectable; scroll synchronized with left pane
- Splitter ratio: 65% left / 35% right
- Status bar: bottom, shows load state, errors, and export confirmations

## Constraints
- `src/editor.py` is the only new file; no existing `src/` files are modified
- `ChordResult` is always the data type passed between layers — never raw strings
- All chord data imported from `src/chords.py` only
- Line wrap disabled in left pane to preserve 1:1 row alignment with right column
- Classify calls serialized through a single worker thread (no concurrent classify calls)
- `--dry-run` produces console output identical to main.py dry-run format; no crash without Csound
- `bridge.close()` is always called in `closeEvent`, not left to atexit alone
- Console always prints chord name + similarity score (CLAUDE.md convention)

## Aesthetic
- Background: `#1a1a1a`; text: `#e0e0e0`; annotation text: `#888888`; pending `...`: `#555555`
- Font: `Menlo, Courier New, monospace` at 13pt for left pane; 12pt for right column
- Window title: "Chord Editor"
- Minimum window size: 900 × 500 px

## Example
```
$ python src/editor.py
[window opens, status bar: "Loading model…"]
[~10s later, status bar clears, left pane becomes active]

[user types "I lost myself today", presses Return]
  → right column: "vi — A minor  0.72"
  → console: Playing vi (A minor) — score: 0.72
  → chord plays

[user types "The light came back", presses Return]
  → right column: "I — C major  0.88"
  → console: Playing I (C major) — score: 0.88
  → chord plays (previous chord interrupted)

[user presses Return on empty line]
  → nothing happens

[user presses Cmd+S]
  → save dialog opens
  → writes poem.json and poem.txt
```
