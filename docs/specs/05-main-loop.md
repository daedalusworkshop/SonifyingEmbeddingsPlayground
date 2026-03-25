# Spec 05: Main Loop

## Intent
Provide an interactive CLI that accepts text input and plays the corresponding chord. Supports single-line REPL mode, file mode (one chord per line), and dry-run mode (no audio).

## Inputs
- stdin (interactive) or `--file PATH` (file mode)
- `--dry-run` flag (skip audio, print results only)
- `--delay SECONDS` (file mode only; seconds between chords, default 2.5)

## Outputs
- Console output per input: chord name, numeral, score
- Audio via CsoundBridge (unless --dry-run)

## Algorithm
1. Parse arguments: `--file`, `--dry-run`, `--delay`
2. Initialize CsoundBridge (unless `--dry-run`; if ctcsound unavailable, auto-enable dry-run with warning)
3. Load classifier (loads model + anchors once)
4. If `--file PATH`:
   a. Read all non-empty lines from file
   b. For each line: classify → print → play (or dry-run print) → sleep(delay)
5. Else (REPL mode):
   a. Print startup banner
   b. Loop: prompt `> `, read line, skip empty, classify → print → play
   c. Exit cleanly on Ctrl+C or empty line with EOF

## Constraints
- Model and anchors load once before the loop begins, not per-input
- Empty input lines are silently skipped
- Ctrl+C triggers graceful shutdown (calls `bridge.close()`)
- `--dry-run` prints all output but never calls any ctcsound function

## Example
```
$ python src/main.py
Sonifying Embeddings — type text, hear its chord. Ctrl+C to quit.

> I miss her so much it hurts
Playing vi (A minor) — score: 0.62

> the sun came out and everything felt possible
Playing I (C major) — score: 0.71

> ^C
Goodbye.
```
