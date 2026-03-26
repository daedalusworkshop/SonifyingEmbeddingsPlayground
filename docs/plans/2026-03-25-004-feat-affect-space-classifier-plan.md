---
title: Affect Space Classifier
type: feat
status: active
date: 2026-03-25
origin: docs/brainstorms/2026-03-25-pure-theory-anchors-brainstorm.md
---

# Affect Space Classifier

## Overview

Replace the current 1024-dim keyword-page cosine classifier with an explicit N-dimensional affect space. Chords are placed at coordinates by an LLM (given a music theory as input); input text maps to the same space via two swappable methods — NRC VAD lexicon and prompted LLM. Classification becomes nearest-chord distance in N-dim space.

The result: **music theory is a config, not code.** Change the theory, re-run the placement script, the system adapts.

---

## Problem Statement

The current system requires a human at the most critical juncture: translating music theory into words the embedding model understands. This is done by hand in `data/chords/*.md`, creating three problems:

1. **Maintenance fragility** — keyword pages drift, must be benchmarked and re-tuned after every change
2. **Opaque failure modes** — when classification breaks, it's unclear whether the problem is the corpus, the model, the instruction prefix, or the temperature
3. **Theory is locked in** — changing the emotional theory means editing 7 markdown files and rerunning benchmarks until something works

The brainstorm (`docs/brainstorms/2026-03-25-pure-theory-anchors-brainstorm.md`) identified the root cause: we're manually writing a bridge the model should build itself. The scratch file (`scratch_theory_anchors.py`) confirmed that pure theory anchors alone (13/34) don't solve this — the model needs emotional scaffolding on the anchor side. The conversation evolved further: don't scaffold with words, scaffold with *coordinates*.

---

## Proposed Solution

### The Insight

An LLM can answer bounded, axis-specific questions about chords far more reliably than it can generate keyword pages. "Where does V sit on the tension axis, 0 to 1?" is a tractable question with a verifiable answer. The query side — mapping input text to the same axes — can be done with a lexicon (fast, transparent) or prompted LLM (accurate).

### The Architecture

```
CHORD PLACEMENT (once, offline):
  music_theory_prompt + chord names
      → LLM places each chord at N-dim coordinates
      → stored as chord_coords.json

QUERY MAPPING (runtime):
  input text
      → NRC VAD lexicon OR prompted LLM
      → N-dim vector

CLASSIFICATION:
  nearest chord by Euclidean distance in N-dim space
```

The embedding model (Qwen) is no longer involved in anchor representation. It may still be used as the "prompted" query mapper. The `.pt` tensor becomes a coordinate matrix `(7, N)` instead of `(7, 1024)`.

---

## Affect Dimensions

Five dimensions, each a float 0.0–1.0:

| Dimension | 0.0 | 1.0 |
|---|---|---|
| **valence** | dark / unpleasant | bright / pleasant |
| **arousal** | still / calm | urgent / kinetic |
| **tension** | resolved | unresolved |
| **direction** | retrospective | anticipatory |
| **expressiveness** | interior / private | raw / open |

These 5 separate the 7 diatonic chords with minimal overlap. Valence + arousal alone (Russell's 2D) conflates ii/vi and I/IV. Tension cleanly separates I from V. Direction separates vi (backward-looking) from ii (forward-leaning). Expressiveness separates iii (interior) from vi (open sorrow).

The dimension set is itself a config — adding a 6th axis costs nothing structurally.

---

## Technical Approach

### New Files

**`src/affect_space.py`**
- Defines `DIMENSIONS: list[str]` — the axis names in order
- Defines `DEFAULT_COORDS: dict[str, list[float]]` — baseline LLM-placed coordinates per chord numeral
- Holds `euclidean_distance(a, b)` and `nearest_chord(query_vec, coord_matrix)` utilities

**`src/query_mapper.py`**
- `class LexiconMapper` — NRC VAD lexicon path; tokenizes input, averages per-word VAD scores, projects to the 5 affect dimensions (valence, arousal map directly; tension/direction/expressiveness require a small projection)
- `class PromptedMapper` — sends input text to an LLM with axis definitions, parses N floats from response
- Common interface: `map(text: str) -> list[float]`

**`scripts/place_chords.py`**
- Takes a `--theory` argument (free text, e.g. `"functional harmony in C major"`)
- Prompts an LLM once per chord: "Given {theory}, rate chord {numeral} ({name}) on each dimension 0.0–1.0"
- Writes output to `data/chord_coords.json`
- Prints the resulting coordinate table for inspection

### Modified Files

**`src/chords.py`**
- Remove `keyword_file: str` from `ChordDef`
- Add `affect_coords: list[float]` (populated at runtime from `data/chord_coords.json`, or from `affect_space.DEFAULT_COORDS` as fallback)

**`src/anchor_builder.py`**
- Add new mode: `build_from_coords()` — reads `data/chord_coords.json`, returns `(7, N)` float tensor
- Keep existing `build()` (embedding-based) behind a flag so current system still runs during transition

**`src/classifier.py`**
- Add `AffectClassifier` class alongside existing `Classifier`
- Uses `query_mapper.map(text)` → N-dim vector, then `affect_space.nearest_chord()` → `ChordResult`
- `CONFIDENCE_THRESHOLD` reinterpreted as max acceptable distance (needs recalibration)
- Temperature sampling: revisit — may not be needed in N-dim space since distances are already continuous

### Deleted Files (Phase 4)
- `data/chords/*.md` — all 7 keyword pages
- `data/anchors.pt` — replaced by `data/chord_coords.json`
- `data/anchors_meta.json` — no longer needed

---

## Implementation Phases

### Phase 1 — Affect Space + Chord Placement Script

- [ ] Write `src/affect_space.py` with dimension definitions and distance utilities
- [ ] Write `scripts/place_chords.py` with `--theory` flag
- [ ] Run placement with `"functional harmony in C major"` and inspect coordinates
- [ ] Run placement with 2–3 alternate theories to verify swappability
- [ ] Store result in `data/chord_coords.json`

Success: coordinates for all 7 chords exist, look musically sensible at a glance, and the I-chord gravity risk is addressed by design (ii and vi clearly separated on expressiveness and direction axes).

### Phase 2 — Query Mapper: Lexicon

- [ ] Write `src/query_mapper.py` with `LexiconMapper`
- [ ] Download or bundle NRC VAD lexicon (public domain, ~20k words)
- [ ] Map valence/arousal directly; define a small linear projection for tension/direction/expressiveness
- [ ] Add `LexiconMapper` as a variant in `scratch_theory_anchors.py` and run the 34-case test
- [ ] Compare against current baseline (24/34)

### Phase 3 — Query Mapper: Prompted

- [ ] Add `PromptedMapper` to `src/query_mapper.py`
- [ ] Design the prompt carefully: axis definitions, expected output format (JSON floats), few-shot examples
- [ ] Run the same 34-case test
- [ ] Compare lexicon vs. prompted — document which wins on which chord types

### Phase 4 — Classifier Integration

- [ ] Write `AffectClassifier` in `src/classifier.py`
- [ ] Wire into `src/main.py` behind a `--affect-space` flag (keep existing classifier default during transition)
- [ ] Run `src/benchmark.py` against both classifiers and compare
- [ ] Calibrate `CONFIDENCE_THRESHOLD` for the new distance metric
- [ ] Update `tests/test_editor_integration.py` to work with either classifier

### Phase 5 — Cleanup

- [ ] Remove `data/chords/*.md` and `data/anchors.pt`
- [ ] Remove `keyword_file` from `ChordDef` in `src/chords.py`
- [ ] Remove embedding-based `build()` from `anchor_builder.py` or retire the file entirely
- [ ] Update `docs/specs/01-chord-corpus.md` — spec no longer applies
- [ ] Update `docs/specs/02-anchor-embeddings.md` — replace with affect space spec (also fix the stale MiniLM reference)
- [ ] Make `AffectClassifier` the default in `src/main.py`

---

## Alternative Approaches Considered

**Pure theory labels embedded via Qwen** (tested in `scratch_theory_anchors.py`)
- Result: 13/34 — the model cannot bridge emotional language → technical chord description without scaffolding on the anchor side
- Rejected: fails completely on ii, iii, IV

**Adjectives-only keyword pages** (tested)
- Result: 24/34 — ties current baseline, fixes vi, hurts IV
- Rejected: still hand-curated, doesn't solve the maintenance problem

**Grounded dense keywords** (tested)
- Result: 25/34 — best tested so far, but vii° becomes a gravity well and V suffers
- Rejected: same fundamental problem — every manually-curated variant has its own gravity well chord

**Current full .md system**
- Result: 24/34 — the baseline
- Extended Phrases add zero accuracy (adjectives-only ties it while being half the text)

---

## System-Wide Impact

### Interaction Graph

`scripts/place_chords.py` (offline) → writes `data/chord_coords.json` → read by `src/affect_space.py` → consumed by `AffectClassifier.__init__()` → `classify()` calls `query_mapper.map()` → returns `ChordResult` → `CsoundBridge.play_chord()` unchanged.

The `ChordResult` datatype is unchanged. Everything downstream of `classifier.py` is unaffected.

### State Lifecycle Risks

- If `data/chord_coords.json` is missing at startup, `AffectClassifier` must fall back to `DEFAULT_COORDS` in `affect_space.py`, not crash
- If the query mapper is `PromptedMapper` and the LLM call fails, fall back to `LexiconMapper`
- Temperature sampling may need to be removed or rethought — in 5D Euclidean space, the existing softmax-over-cosine-scores approach doesn't directly apply

### I-Chord Gravity Risk

Documented in `docs/solutions/logic-errors/2026-03-25-i-chord-gravity-argmax.md`: any chord with a broad or central position in affect space will absorb ambiguous inputs. Mitigation: the LLM placement step must be reviewed to ensure no chord occupies the geometric centroid of the space. The expressiveness and direction axes exist specifically to pull I (interior, retrospective) away from IV (open, departing) and ii (forward-leaning).

### MPS / Thread Safety

`PromptedMapper` uses Qwen in inference mode. If run inside a QThread (editor.py), apply the same MPS workaround documented in `docs/solutions/runtime-errors/2026-03-25-mps-qthread-device-mismatch.md`. `LexiconMapper` is CPU-only and thread-safe.

---

## Acceptance Criteria

- [ ] `scripts/place_chords.py --theory "..."` runs without error and produces `data/chord_coords.json`
- [ ] Different `--theory` inputs produce observably different coordinate matrices
- [ ] `AffectClassifier` with `LexiconMapper` scores ≥ 24/34 on `scratch_theory_anchors.py` test suite
- [ ] `AffectClassifier` with `PromptedMapper` is also benchmarked and compared
- [ ] `src/benchmark.py` scores ≥ current baseline (24/34) with the best query mapper
- [ ] No `data/chords/*.md` files remain in the final state
- [ ] `src/main.py --dry-run` works end-to-end with the new classifier
- [ ] `docs/specs/02-anchor-embeddings.md` updated and no longer references MiniLM

---

## Success Metrics

- Benchmark: ≥ 24/34 on the 34-case `scratch_theory_anchors.py` suite
- Benchmark: ≥ current score on `src/benchmark.py` 10-case suite
- Swappability: 2+ different music theories produce different, musically-sensible coordinate placements
- Zero keyword files remain in the repo
- A new chord can be added by editing `chords.py` and re-running `scripts/place_chords.py` — no markdown authoring

---

## Dependencies & Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| I-chord gravity in coordinate space | Medium | Explicit axis design (direction + expressiveness) separates it by construction |
| LexiconMapper projection for non-VAD axes | Medium | Tension/direction/expressiveness need a small hand-defined mapping from VAD — this is transparent and auditable |
| PromptedMapper output parsing brittleness | Low | JSON-structured output with schema validation; fallback to lexicon |
| CONFIDENCE_THRESHOLD needs recalibration | Certain | Distance metric is different; threshold must be set empirically after Phase 4 |
| Benchmark argmax vs. sampling divergence | Existing | Already flagged in plan `2026-03-25-003`; `classify_deterministic()` should be added |

---

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-03-25-pure-theory-anchors-brainstorm.md](docs/brainstorms/2026-03-25-pure-theory-anchors-brainstorm.md)
  - Key decisions carried forward: remove `.md` files entirely; trust model's inherent knowledge of chord emotion; no manual keyword tuning loop
  - Significantly evolved in conversation: the approach shifted from "embed theory labels" to "LLM places chords at explicit affect-space coordinates" after `scratch_theory_anchors.py` showed theory-label embeddings score 13/34

### Internal References

- Current classifier: `src/classifier.py:12–18` (constants), `src/classifier.py:26–60` (classify method)
- Anchor builder coupling point: `src/anchor_builder.py` → `data/anchors.pt` shape `(7, 1024)`
- ChordDef to modify: `src/chords.py:9–18`
- Benchmark suite: `src/benchmark.py:28–41`
- I-chord gravity documented fix: `docs/solutions/logic-errors/2026-03-25-i-chord-gravity-argmax.md`
- Corpus leakage risk: `docs/solutions/best-practices/2026-03-25-chord-corpus-section-leakage.md`
- MPS thread safety: `docs/solutions/runtime-errors/2026-03-25-mps-qthread-device-mismatch.md`
- Stale spec to fix: `docs/specs/02-anchor-embeddings.md` (still references MiniLM 384-dim)
- Existing scratch test: `scratch_theory_anchors.py` (34-case suite, 3 variants already benchmarked)
