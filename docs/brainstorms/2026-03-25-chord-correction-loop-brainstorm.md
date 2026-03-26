---
date: 2026-03-25
topic: chord-correction-loop
---

# Chord Correction Loop

## What We're Building

A three-phase system for improving the model's chord intuition from within the Mac app:

1. **Correction UI** — right-click any chord annotation in the editor to get a context menu with all 7 chords; selecting one overrides the auto classification and saves the correction
2. **Corrections store** — a flat `data/corrections.jsonl` file where each entry records the line, the auto-classified chord, the user's correction, and a timestamp; this becomes the living benchmark
3. **Auto-research loop** — a CLI script (`src/auto_improve.py`) that reads corrections, finds where the current system still fails, asks Claude to propose edits to the chord keyword pages, rebuilds anchors, re-tests, and reports the delta

## Why This Approach

Considered per-session files with an in-app loop trigger (Approach B), but chose flat JSONL + CLI script (Approach A) for simplicity: one file is easy to inspect, git-diff, and reason about. The loop being a CLI script keeps it auditable and explicit — you control when it runs. UI trigger can be added later once the loop is proven.

## Key Decisions

- **Trigger:** Right-click on chord annotation → context menu with 7 chord options
- **Storage:** `data/corrections.jsonl`, append-only, one JSON object per line
- **Entry shape:** `{"line": "...", "auto": "vi", "correct": "ii", "timestamp": "2026-03-25T..."}`
- **Benchmark:** `corrections.jsonl` replaces/augments the hardcoded benchmark in `src/benchmark.py`
- **Auto-research loop:** Hill-climbing explorer — not targeted patching. Each iteration: run full benchmark → find failures → hypothesize an edit to any keyword page → rebuild anchors → re-run full benchmark → accept if net improvement (more passes, no new regressions), otherwise revert → repeat
- **Regression safety is the core constraint:** every proposed change is validated against the entire corrections set before being accepted, not just the case it was targeting
- **Loop target:** Only keyword pages (`data/chords/*.md`) are modified — not model weights, temperature, or thresholds

## Open Questions

- How many correction examples before the loop is worth running? (Suggested minimum: ~10)

## Next Steps

→ `/ce:plan` for implementation details
