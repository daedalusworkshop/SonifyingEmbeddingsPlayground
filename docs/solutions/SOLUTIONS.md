# Solutions Index

Institutional knowledge base — discovered bugs, root causes, and fixes.
Searched by the `learnings-researcher` agent before starting new work.

## Architecture
- [How we map words to chords: the emotional embedding approach](architecture/2026-03-25-words-to-chords-approach.md) — full pipeline: corpus → anchors → cosine similarity → temperature sampling; what works, what doesn't, how to tune

## Runtime Errors
- [MPS device mismatch crashes classifier inside QThread](runtime-errors/2026-03-25-mps-qthread-device-mismatch.md) — anchors.pt cached on MPS + QThread can't use MPS; force CPU + `.cpu()` anchors

## Logic Errors
- [I chord absorbs ambiguous inputs via argmax + tie-breaking](logic-errors/2026-03-25-i-chord-gravity-argmax.md) — fix: sharpen I-tonic.md corpus + replace argmax with temperature sampling (T=0.05)

## Best Practices
- [Corpus section leakage: Contrasting/Atmospheric sections hurt anchor separation](best-practices/2026-03-25-chord-corpus-section-leakage.md) — keep only Core Adjectives + Extended Phrases; never reference other chords in a page
- [Model upgrade MiniLM → Qwen: threshold + instruction prefix both must change](best-practices/2026-03-25-model-upgrade-minilm-to-qwen.md) — Qwen needs CONFIDENCE_THRESHOLD=0.40 and matching instruction prefix on both anchor + query sides
