# Brainstorm: Pure Theory Anchors

**Date:** 2026-03-25
**Status:** Draft

---

## What We're Building

Replace the hand-curated `data/chords/*.md` emotional keyword pages with purely technical music theory descriptions of each chord — and embed those as anchors instead.

No emotional language. No affective keywords. Just what each chord **is** technically:

```
"I chord: C major triad (C-E-G), tonic function, first scale degree, C major"
"V chord: G major triad (G-B-D), dominant function, fifth scale degree, C major"
```

The model (Qwen3-Embedding-0.6B) is trusted to bridge user input ("I feel tense and unresolved") to the correct harmonic object ("dominant") without any qualitative scaffolding on the anchor side.

---

## Why This Approach

The current system uses ~200-word emotional keyword pages per chord as anchors. This creates two problems:

1. **Maintenance overhead** — the pages are hand-curated and drift; they bake in assumptions about what emotions belong to each chord
2. **Potential noise** — the keyword pages may diverge from the model's own internal chord→emotion associations, creating friction rather than alignment

The bet here: Qwen3-Embedding has absorbed enormous amounts of music theory and emotional language during training. It already knows that "dominant" creates tension, that "tonic" means rest, that "subdominant" is pensive. Pointing it at a pure technical description lets its own knowledge do the work — we stop fighting the model and start trusting it.

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Anchor content | Pure technical music theory | Notes, function, scale degree — nothing qualitative |
| Source location | Inline in `chords.py` (`ChordDef.theory_label`) | Single source of truth, versioned with chord definitions |
| `.md` files | Delete entirely | No longer needed |
| `anchor_builder.py` | Keep, simplified | Still embeds and caches `.pt` for fast startup |
| `data/chords/` directory | Remove | Eliminated with the `.md` files |
| Instruction prefix (anchor side) | **Open question** | See below |

---

## Architecture Change

**Before:**
```
data/chords/*.md  →  anchor_builder.py  →  data/anchors.pt  →  classifier.py
```

**After:**
```
src/chords.py (theory_label field)  →  anchor_builder.py  →  data/anchors.pt  →  classifier.py
```

Each `ChordDef` gains a `theory_label: str` field. `anchor_builder.py` reads `chord.theory_label` instead of loading markdown files. Everything downstream is unchanged.

---

## Open Questions

1. **Instruction prefix mismatch** — The current instruction tells the model to embed for "emotional and affective character." If the anchor is now purely technical, does the same instruction still work? Or should the anchor side use a different instruction (e.g., "Represent this musical chord by its harmonic function and theoretical identity")? This is the highest-risk design question.

2. **Model knowledge gap** — Will the model correctly distinguish between closely-related chords (e.g., ii vs. IV, or iii vs. vi) when the anchor is purely technical and the query is emotional? These pairs are functionally similar; the keyword pages currently help pull them apart.

3. **Benchmark delta** — Need to run `src/benchmark.py` before and after to measure the effect. The 10-case benchmark is the primary quantitative signal.

---

## Resolved Questions

*(none yet)*

---

## Success Criteria

- Benchmark scores on `src/benchmark.py` equal or improve
- Classification "feels right" on intuitive test inputs
- `data/chords/` directory removed; no hand-curated emotional files remain
