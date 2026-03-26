---
title: "Argmax + tie-breaking caused I chord to absorb most ambiguous inputs"
date: 2026-03-25
module: classifier
problem_type: logic_error
component: chord_classifier
severity: high
symptoms:
  - "Ambiguous or generic text nearly always classifies as I (C major)"
  - "Benchmark plateau: hard to break past ~6-7/10 on varied test cases"
  - "Chords like IV, vi, ii rarely appear in practice even for fitting inputs"
root_cause: logic_error
tags:
  - classifier
  - argmax
  - temperature-sampling
  - I-chord
  - confidence
---

## Problem

The original classifier used argmax over cosine scores with a tie-breaking priority
list (`TIE_BREAK_ORDER`). I was listed first in the priority order. Because
`I-tonic.md` used broad positive/neutral vocabulary (happiness, peace, everyday
comfort), its anchor embedding was close to many generic inputs. When scores were
within the tie tolerance of 0.02, I almost always won the tiebreak. Result: most
ambiguous text defaulted to I, making the system feel monotonic.

## Root Cause

Two compounding issues:
1. `I-tonic.md` described everyday positive states rather than the specific emotional
   quality of tonal resolution — so its anchor vector was broadly "positive" rather
   than distinctively "home."
2. Argmax with tie-breaking eliminates the natural distribution of close scores.
   When three chords are within 0.02 of each other, sampling proportionally would
   spread results; argmax collapses them to one winner.

## Solution

**Two-pronged fix — both were required:**

1. **Corpus rewrite:** Rewrote `I-tonic.md` to focus exclusively on tonal resolution,
   homecoming, and arrival. Added explicit exclusion phrases for everyday comfort,
   generic happiness, and contentment (which belong to IV). This sharpened the anchor
   vector to be distinctively "resolution" rather than "positive."

2. **Temperature sampling:** Replaced argmax + tie-breaking with softmax temperature
   sampling (`T=0.05`). Scores are divided by temperature before softmax → very
   peaked distribution that still respects the best score, but samples proportionally
   among close competitors rather than always picking the priority winner.

```python
TEMPERATURE = 0.05  # lower → closer to argmax; higher → more harmonic variety

probs = torch.softmax(scores_tensor / TEMPERATURE, dim=0)
chosen_idx = int(torch.multinomial(probs, 1).item())
```

Benchmark result after both changes: 9/10.

## Prevention

- When adding or editing chord keyword pages, focus on the *distinctive* emotional
  character of that chord — not general positive/negative valence.
- Each page should implicitly exclude neighboring chords' territory. Write what makes
  this chord *different*, not just what it *is*.
- The `Contrasting with Neighbors` section in keyword pages was later removed entirely
  (see: refactor commit 19ff9f3) because it leaked neighboring vocabulary into anchors.
- Keep `TEMPERATURE = 0.05` unless you want more variety at the cost of accuracy.
  Do not revert to argmax.
