# Spec 02: Anchor Embeddings

## Intent
Build and cache one 384-dimensional embedding vector per chord by encoding its full keyword page as a single string. These anchor vectors are the embedding-space representation of each chord's emotional character.

## Inputs
- 7 keyword pages from `data/chords/*.md`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

## Outputs
- `data/anchors.pt` — a `torch.Tensor` of shape (7, 384), rows ordered by chord index (I=0, ii=1, iii=2, IV=3, V=4, vi=5, vii°=6)
- Console-printed 7×7 pairwise cosine similarity matrix (at build time, for validation)

## Algorithm
1. Load all 7 keyword page files from `data/chords/` in canonical chord order
2. For each file, concatenate all text content into a single string (strip markdown headers, keep the words)
3. Encode all 7 strings in one batch: `model.encode(texts, convert_to_tensor=True)`
4. Compute and print the 7×7 pairwise cosine similarity matrix using `util.cos_sim()`
5. Assert all off-diagonal values < 0.85; warn loudly if any exceed this threshold
6. Save the tensor to `data/anchors.pt` using `torch.save()`
7. Save a hash of each keyword page alongside the tensor (for staleness detection)

## Constraints
- Embed the full page as one string — do NOT average individual word embeddings
- The chord order in the output tensor must match `CHORD_ORDER` in `src/chords.py`
- Cache is stale if any keyword page's hash has changed since last build — auto-rebuild in that case
- Model name is read from this spec's `## Inputs` section; changing it here triggers a rebuild

## Example
Input: `data/chords/vi-submediant.md` (full text, ~250 words)
Output: one 384-dimensional float32 tensor at row index 5

## Staleness Detection
Store a JSON sidecar `data/anchors_meta.json`:
```json
{
  "model": "all-MiniLM-L6-v2",
  "hashes": {
    "I-tonic.md": "<sha256>",
    ...
  }
}
```
On load, recompute hashes and compare. Rebuild if any differ.
