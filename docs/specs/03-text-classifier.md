# Spec 03: Text Classifier

## Intent
Given any input string, return the diatonic chord whose anchor embedding is most semantically similar to the embedded input. Return a structured `ChordResult` with the winning chord and all similarity scores.

## Inputs
- `text: str` — any input string
- `data/anchors.pt` — prebuilt anchor embeddings (loaded once at startup)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (same model as anchor builder)

## Outputs
- `ChordResult` dataclass with fields:
  - `numeral: str` — e.g. "vi"
  - `name: str` — e.g. "A minor"
  - `score: float` — cosine similarity of best match (0–1)
  - `all_scores: dict[str, float]` — scores for all 7 chords
  - `midi_notes: list[int]` — MIDI note numbers for this chord
  - `frequencies: list[float]` — frequencies in Hz
  - `low_confidence: bool` — True if score < 0.15

## Algorithm
1. Load anchors from `data/anchors.pt` (rebuild via anchor_builder if stale)
2. Encode `text` with the same model: `model.encode(text, convert_to_tensor=True)`
3. Compute cosine similarity against all 7 anchors: `util.cos_sim(text_emb, anchors)` → shape (1, 7)
4. Extract scores as a float list
5. Find the index of the maximum score
6. If max score < 0.15: set `low_confidence=True`, use index 0 (I, tonic) as fallback
7. If top two scores are within 0.02 of each other: break tie using functional harmony priority (I > IV > V > vi > ii > iii > vii°)
8. Return populated `ChordResult`

## Constraints
- The model used to encode input text must be identical to the model used to build anchors
- Anchors are loaded once at process startup, not on every call
- Empty string input returns `ChordResult` for I with `low_confidence=True`

## Example
Input: `"I miss her so much it hurts"`
Expected output: `ChordResult(numeral="vi", name="A minor", score=~0.62, low_confidence=False)`
