---
title: "Upgrading from all-MiniLM-L6-v2 to Qwen3-Embedding-0.6B requires threshold and instruction changes"
date: 2026-03-25
module: classifier
problem_type: best_practice
component: chord_classifier
severity: medium
symptoms:
  - "After model swap, nearly all inputs fall below the confidence threshold"
  - "Cosine scores are systematically higher with Qwen than MiniLM"
  - "Classification quality improves but calibration is off"
root_cause: config_error
tags:
  - qwen
  - minilm
  - model-upgrade
  - confidence-threshold
  - instruction-prefix
  - embeddings
---

## Problem

The MVP used `all-MiniLM-L6-v2` (384-dim, no instruction awareness). When upgrading
to `Qwen/Qwen3-Embedding-0.6B` (1024-dim, instruction-aware), two things broke:

1. **Threshold mismatch:** Qwen produces higher absolute cosine scores than MiniLM.
   The original `CONFIDENCE_THRESHOLD = 0.15` was too low — basically everything
   passed. Conversely, if you raised it to MiniLM-calibrated values, many valid
   inputs would fail. The threshold needed to be recalibrated for Qwen's score range.

2. **Missing instruction prefix:** Qwen3-Embedding is instruction-aware. Without the
   instruction prefix, it behaves as a general-purpose embedder rather than an
   emotionally-focused one. Both anchor pages and query text must use the same prefix.

## Solution

Set `CONFIDENCE_THRESHOLD = 0.40` for Qwen (vs 0.15 for MiniLM).

Add instruction prefix to both anchor encoding (`anchor_builder.py`) and query
encoding (`classifier.py`):

```python
INSTRUCTION = (
    "Instruct: Represent this text by its emotional and affective character "
    "for matching to a musical chord.\nQuery: "
)

# In classifier.classify():
text_emb = self.model.encode(
    INSTRUCTION + text,
    convert_to_tensor=True,
    normalize_embeddings=True,
)

# In anchor_builder.py — same prefix applied to each chord page
```

Rebuild `data/anchors.pt` after any model or prefix change.

## Prevention

- The confidence threshold is model-specific. Never copy it between models without
  recalibration. Document it in `CLAUDE.md` alongside the model name.
- Instruction-aware models (Qwen, E5-instruct, etc.) require matching prefixes on
  both sides (anchor + query). Asymmetric prefixes silently degrade quality.
- After a model change: rebuild anchors, run `src/benchmark.py --silent`, check
  scores. A sudden drop in benchmark pass rate usually means threshold needs tuning.
- `normalize_embeddings=True` is required for cosine similarity to work correctly
  with Qwen — ensure it's set in both anchor building and classification.
