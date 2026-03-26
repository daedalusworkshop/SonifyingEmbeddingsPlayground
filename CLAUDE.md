# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SonifyingEmbeddingsPlayground — Project Constitution

## What This Is

A pipeline that maps any text to a diatonic chord via emotional embeddings, then synthesizes that chord in real time with Csound. The emotional bridge: rich keyword pages per chord → anchor embeddings → cosine similarity classification.

## Doc-Driven Development

**The specs in `docs/specs/` are the source of truth. Code is a compilation artifact.**

- Each file in `docs/specs/` describes exactly one process (intent, inputs, outputs, algorithm, constraints, example)
- When a spec changes, the corresponding code is regenerated to match the spec
- If code and spec disagree, fix the spec first, then regenerate the code
- Atomic scope: one spec = one module or function boundary

**To change a behavior:**
1. Edit the relevant spec in `docs/specs/`
2. Re-run `anchor_builder.py` if the chord corpus or embedding spec changed (this regenerates `data/anchors.pt`)
3. Rewrite the corresponding source file to match the updated spec

## Key Architectural Decisions

- **Embedding model:** `Qwen/Qwen3-Embedding-0.6B` (local, 1024-dim, instruction-aware)
- **Instruction prefix:** applied to both anchor pages and query text — tells model to focus on emotional/affective character
- **Anchor strategy:** embed each chord's full keyword page (with instruction prefix) → single 1024-dim normalized vector
- **Classification:** cosine similarity; confidence threshold 0.15; tie-break by functional harmony priority
- **Audio:** ctcsound + CsoundPerformanceThread (Csound 6.18 installed); orchestra in `instruments/pad.orc`
- **Key:** C major, root-position triads, octave 4

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
# Optional: pip install ctcsound PyQt6
```

**Run the app:**
```bash
python src/main.py              # interactive REPL
python src/main.py --dry-run    # no Csound required
python src/main.py --file poem.txt --delay 3.0
python src/editor.py            # PyQt6 GUI
```

**Rebuild anchor embeddings** (after editing `data/chords/*.md` or changing the embedding spec):
```bash
python src/anchor_builder.py
```

**Run tests:**
```bash
python tests/test_chord_stopping.py      # 4 tests: voice stopping behavior
python tests/test_editor_integration.py # 7 tests: PyQt6 GUI (requires offscreen display)
```

**Run benchmark:**
```bash
python src/benchmark.py   # 10 hand-curated test cases, interactive (Enter/r/q)
python src/benchmark.py --silent
```

## File Layout

```
data/chords/*.md      — emotional keyword pages (one per chord, edit freely)
data/anchors.pt       — cached anchor embeddings (auto-regenerated, do not edit)
docs/specs/           — atomic process specs (source of truth)
src/                  — Python source (derived from specs)
instruments/pad.orc   — Csound orchestra
```

## Module Roles

| File | Role |
|------|------|
| `src/chords.py` | Chord definitions only — `ChordDef` and `ChordResult` dataclasses, 7 chord entries |
| `src/classifier.py` | Loads model + anchors, embeds input, cosine similarity, temperature sampling (T=0.05) |
| `src/anchor_builder.py` | Reads `data/chords/*.md`, builds/caches `data/anchors.pt`; checks staleness via file hashes |
| `src/csound_bridge.py` | Manages ctcsound lifecycle; instr 1 = chord voice, instr 2 = tonic drone, instr 99 = kill |
| `src/main.py` | CLI entry point; wires Classifier → CsoundBridge |
| `src/editor.py` | PyQt6 GUI; `ClassifierWorker` runs in QThread with forced CPU (MPS bug workaround) |

## Conventions

- `ChordResult` is the central data type — always pass it between layers, never raw strings
- All 7 chord definitions live in `src/chords.py` only — no other file hardcodes chord data
- Console always prints chord name + similarity score when a chord is selected
- `--dry-run` must work without Csound installed
- Confidence threshold is **0.40** (Qwen-specific; higher than MiniLM default of 0.15)
