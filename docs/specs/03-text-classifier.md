# Spec 03: Text Classifier

## Intent
Given any input string, return the diatonic chord whose anchor embedding is most semantically similar to the embedded input. Return a structured `ChordResult` with the winning chord and all similarity scores.

## Inputs
- `text: str` — any input string
- `data/anchors.pt` — prebuilt anchor embeddings (loaded once at startup)
- Embedding model: `Qwen/Qwen3-Embedding-0.6B` (same model as anchor builder)

## Outputs
- `ChordResult` dataclass with fields:
  - `numeral: str` — e.g. "vi"
  - `name: str` — e.g. "A minor"
  - `score: float` — cosine similarity of the sampled chord
  - `all_scores: dict[str, float]` — scores for all 7 chords
  - `midi_notes: list[int]` — MIDI note numbers for this chord
  - `frequencies: list[float]` — frequencies in Hz
  - `low_confidence: bool` — True if best score < 0.40

## Algorithm
1. Load anchors from `data/anchors.pt` (rebuild via anchor_builder if stale)
2. Encode input with instruction prefix: `model.encode(INSTRUCTION + text, normalize_embeddings=True)`
3. Compute cosine similarity against all 7 anchors → shape (1, 7)
4. Extract scores as a float list
5. Set `low_confidence = True` if `max(scores) < 0.40`
6. Apply temperature sampling: compute `softmax(scores / TEMPERATURE)` and sample one chord index
7. Return populated `ChordResult` with the sampled chord and its score

## Parameters
- `CONFIDENCE_THRESHOLD = 0.40` — Qwen scores are compressed into a higher range than MiniLM
- `TEMPERATURE = 0.05` — controls sampling sharpness; lower approaches argmax, higher adds harmonic variety
  - At T=0.05: strong-signal text (gap > 0.10) reliably picks the dominant chord; ambiguous text
    (gap < 0.05) samples proportionally, producing natural variety instead of always defaulting to I

## Instruction prefix
```
Instruct: Represent this text by its emotional and affective character for matching to a musical chord.
Query: <text>
```

## Constraints
- The model used to encode input text must be identical to the model used to build anchors
- Anchors are loaded once at process startup, not on every call
- Empty string input returns `ChordResult` for I with `low_confidence=True`, no sampling
- Temperature sampling replaces both argmax and tie-breaking; ties are resolved probabilistically

## Example
Input: `"I miss her so much it hurts"`
Expected output: `ChordResult(numeral="vi", name="A minor", score=~0.71, low_confidence=False)`
