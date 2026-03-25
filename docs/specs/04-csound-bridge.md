# Spec 04: Csound Bridge

## Intent
Manage the ctcsound lifecycle and expose a `play_chord()` function that triggers a chord in real time given a `ChordResult`. New chords interrupt any currently playing notes.

## Inputs
- `ChordResult` from the text classifier
- `instruments/pad.orc` — Csound orchestra file
- Csound 6.18 (verified installed at `/opt/homebrew/bin/csound`)

## Outputs
- Real-time audio to system default output device (`-odac`)
- Console line: `Playing [numeral] ([name]) — score: [x.xx][  LOW CONFIDENCE]`

## Algorithm
1. On `CsoundBridge.__init__()`:
   a. Create `ctcsound.Csound()` instance
   b. Set options: `-odac`, `-d` (suppress Csound console noise)
   c. Read orchestra from `instruments/pad.orc` via `c.compileOrc()`
   d. Load a dummy score to keep engine alive: `c.readScore("f0 3600")`
   e. Call `c.start()`
   f. Create `CsoundPerformanceThread(c.csound())` and call `pt.play()`
   g. Register `atexit` handler to call `pt.stop()`, `pt.join()`, `c.cleanup()`

2. On `play_chord(chord_result: ChordResult)`:
   a. Print feedback line to console
   b. Send `turnoff` to stop any currently playing notes: `pt.inputMessage("i -1 0 0")`
   c. For each frequency in `chord_result.frequencies`:
      - `pt.scoreEvent(False, 'i', [1, 0, DURATION, AMPLITUDE, freq])`
   d. DURATION = 2.0 seconds, AMPLITUDE = 0.4

3. On `CsoundBridge.close()`:
   - Stop thread, join, cleanup, reset

## Constraints
- `CsoundBridge` is a singleton — instantiate once at startup
- If ctcsound import fails, raise `CsoundNotAvailableError` (caught by main.py to enable dry-run mode)
- Orchestra file path is relative to project root

## Example
Input: `ChordResult(numeral="IV", name="F major", frequencies=[349.23, 440.00, 523.25])`
Effect: Three notes play simultaneously for 2 seconds at the specified frequencies
Console: `Playing IV (F major) — score: 0.71`
