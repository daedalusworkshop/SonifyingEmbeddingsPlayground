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

- **Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (local, 384-dim, sub-100ms CPU)
- **Anchor strategy:** embed each chord's full keyword page as one concatenated string → single 384-dim vector
- **Classification:** cosine similarity; confidence threshold 0.15; tie-break by functional harmony priority
- **Audio:** ctcsound + CsoundPerformanceThread (Csound 6.18 installed); orchestra in `instruments/pad.orc`
- **Key:** C major, root-position triads, octave 4

## File Layout

```
data/chords/*.md      — emotional keyword pages (one per chord, edit freely)
data/anchors.pt       — cached anchor embeddings (auto-regenerated, do not edit)
docs/specs/           — atomic process specs (source of truth)
src/                  — Python source (derived from specs)
instruments/pad.orc   — Csound orchestra
```

## Conventions

- `ChordResult` is the central data type — always pass it between layers, never raw strings
- All 7 chord definitions live in `src/chords.py` only — no other file hardcodes chord data
- Console always prints chord name + similarity score when a chord is selected
- `--dry-run` must work without Csound installed
