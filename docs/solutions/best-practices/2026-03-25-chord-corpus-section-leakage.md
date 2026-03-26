---
title: "Contrasting and Atmospheric sections in keyword pages leak neighboring vocabulary into anchors"
date: 2026-03-25
module: chord_corpus
problem_type: best_practice
component: chord_classifier
severity: medium
symptoms:
  - "Anchor separation scores are higher than expected between neighboring chords"
  - "Chords that should be distinct (e.g. I vs IV) classify the same inputs"
  - "Adding more keywords to a page doesn't improve accuracy"
root_cause: logic_error
tags:
  - corpus
  - anchor-embeddings
  - section-leakage
  - keyword-pages
---

## Problem

The original chord keyword pages had four sections:
1. Core Adjectives
2. Extended Phrases
3. Atmospheric Contexts
4. Contrasting with Neighbors

The "Contrasting with Neighbors" section explicitly mentioned other chords' vocabulary
(e.g., "unlike the yearning of V, this chord settles"). The embedding model encodes
the full page — including the contrast text — so the anchor for chord X contained
signal about chord Y's vocabulary. This reduced inter-anchor separation and made the
classifier less discriminative.

"Atmospheric Contexts" added low-signal, generic descriptive text that diluted the
distinctive emotional character of each chord.

## Solution

Remove both sections from all keyword pages. Keep only:
1. **Core Adjectives** — the single most important section; highly distinctive terms
2. **Extended Phrases** — fuller emotional descriptions, still specific to this chord

This was done in commit 19ff9f3 across all 6 non-I chord pages.

## Prevention

- When writing or editing `data/chords/*.md`, never reference other chords by name
  or describe what this chord is *not*. The embedding model will encode that negation
  as presence.
- Keep pages focused: what is the *unique emotional signature* of this chord?
- After any significant corpus edit, rebuild anchors and check pairwise similarities:
  `python src/anchor_builder.py` prints separation stats.
- Rule of thumb: if a section could appear in more than one chord's page, it probably
  doesn't belong in any of them.
