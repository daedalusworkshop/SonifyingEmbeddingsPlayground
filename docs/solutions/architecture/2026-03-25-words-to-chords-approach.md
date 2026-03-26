---
title: "How we map words to chords: the emotional embedding approach"
date: 2026-03-25
module: classifier
problem_type: best_practice
component: chord_classifier
severity: low
symptoms: []
root_cause: inadequate_documentation
tags:
  - architecture
  - embeddings
  - classification
  - chord-corpus
  - cosine-similarity
  - temperature-sampling
  - qwen
---

## The Core Idea

We never teach the model what a chord *is*. Instead, we describe what each chord
*feels like* — in plain, evocative language — and then ask: which chord's emotional
description is most similar to this text?

The result is a classification system with no labeled training data, no fine-tuning,
and no music theory hardcoded anywhere. The only human input is the corpus of
emotional descriptions. Everything else is cosine similarity.

---

## The Pipeline

```
input text
    ↓
instruction prefix + text
    ↓  [Qwen3-Embedding-0.6B]
1024-dim normalized vector
    ↓
cosine similarity against 7 anchor vectors
    ↓
temperature sampling (T=0.05)
    ↓
ChordResult
```

---

## Step 1: The Chord Corpus

Each of the 7 diatonic chords in C major has a keyword page in `data/chords/*.md`.
These pages are the soul of the system — their quality determines classification quality
more than any model or parameter choice.

Each page contains:
- **Core Adjectives** — 20–30 single words capturing the chord's emotional signature
- **Extended Phrases** — 10–15 fuller sentence-fragment descriptions

The vocabulary comes from the **Hevner Adjective Circle** (1935), a foundational study
mapping musical qualities to emotional clusters, plus empirical chord-emotion research.

**Critical constraint:** pages must be emotionally *distinctive*, not theoretically
descriptive. "Major third above the root" teaches the model nothing useful.
"Triumphant arrival, the tension finally released" does.

**Chord → emotional character mapping:**
| Chord | Character |
|-------|-----------|
| I     | Resolution, homecoming, tonal arrival — *not* generic happiness |
| ii    | Longing, gentle melancholy, anticipation |
| iii   | Ambiguity, searching, wistfulness |
| IV    | Warmth, openness, generous comfort |
| V     | Tension, expectation, forward motion |
| vi    | Introspection, sadness, emotional depth |
| vii°  | Instability, urgency, unresolved dissonance |

---

## Step 2: Anchor Embeddings

Each keyword page is encoded into a single 1024-dimensional vector — the chord's
"anchor" in embedding space. This is done once and cached to `data/anchors.pt`.

The full page is embedded as one string (not averaged word-by-word). This gives the
model the full semantic context of the page, not just isolated word representations.

The same instruction prefix used at query time is applied here:
```
Instruct: Represent this text by its emotional and affective character
for matching to a musical chord.
Query: <full page text>
```

**Anchor quality check:** after building, print the 7×7 pairwise cosine similarity
matrix. All off-diagonal pairs should be < 0.85. Values above this mean two chords'
descriptions are too similar — the pages need to be more distinctive.

---

## Step 3: Classifying Input Text

At inference time:
1. Prepend the same instruction prefix to the input text
2. Encode with Qwen3-Embedding → 1024-dim normalized vector
3. Compute cosine similarity against all 7 anchor vectors
4. Apply temperature sampling to pick a chord

**Why instruction prefix matters:** Qwen3-Embedding is instruction-aware. Without
the prefix, it embeds text for general semantic similarity. With the prefix, it
focuses specifically on emotional/affective character. This is the difference between
"these words are about work" and "this text feels anxious and pressured."

**Why temperature sampling instead of argmax:**
- Argmax always returns the single best match — for ambiguous inputs, this makes the
  system feel monotonic (usually defaults to the most generic anchor, historically I)
- Temperature sampling at T=0.05 is nearly argmax for clear inputs (gap > 0.10),
  but samples proportionally for ambiguous inputs (gap < 0.05)
- Result: strong emotional text reliably hits the right chord; ambiguous text produces
  natural harmonic variety rather than always collapsing to one chord

**Confidence threshold (0.40 for Qwen):** if the best score is below this, the result
is flagged `low_confidence=True`. The chord is still returned (sampled from the
distribution), but callers can treat it as uncertain. Qwen's scores sit higher than
MiniLM's — 0.40 for Qwen is equivalent to ~0.15 for MiniLM.

---

## What This Approach Is Good At

- **Zero-shot generalization:** any text, in any style, can be classified — no domain
  restriction, no training examples needed
- **Human-steerable:** the corpus is plain English. Improving classification means
  editing `.md` files, not retraining models
- **Transparent:** every classification comes with all 7 scores — you can always see
  *why* a chord was chosen and how close the runners-up were
- **Fast at inference:** model loads once; each classify call is just one encode +
  7 dot products

## What This Approach Is Not Good At

- **Irony and negation:** "I'm not sad at all" may still score high on vi if the
  surrounding emotional vocabulary is there
- **Very short inputs:** one or two words have less signal than a full sentence;
  scores tend to compress toward the center
- **Grammatical structure:** the model reads meaning, not syntax — word order beyond
  semantic content has little effect

---

## Tuning the System

The three levers, in order of impact:

1. **Corpus quality** (highest impact) — rewrite keyword pages. Focus on emotional
   distinctiveness. Each chord should describe a feeling that *couldn't* belong to
   any other chord. Run `anchor_builder.py` and check pairwise similarities after
   every significant edit. Run `benchmark.py` to validate against test cases.

2. **Temperature** (medium impact) — raise `TEMPERATURE` for more variety at the
   cost of accuracy; lower it toward argmax for more determinism. Range: 0.01–0.20.
   Current: 0.05.

3. **Confidence threshold** (low impact, diagnostic) — adjust only when the model
   changes. Use `benchmark.py --silent` to check how many inputs are flagged low_confidence
   at a given threshold.

---

## The Benchmark

`src/benchmark.py` contains 10 hand-curated test cases — one sentence per chord plus
a few edge cases. It's the primary tool for evaluating any corpus or parameter change.

Rule: never accept a corpus edit that reduces benchmark score, even if the targeted
input improves. The full set must not regress.

Current benchmark score: **9/10**.
