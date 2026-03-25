---
title: "feat: Text-to-Chord Sonification MVP"
type: feat
status: active
date: 2026-03-25
---

# feat: Text-to-Chord Sonification MVP

## Overview

Build a pipeline that takes any text input and outputs the most emotionally resonant diatonic chord from the 7 chords of C major, synthesized in real time via Csound. The system uses semantic embeddings to map emotional valence in text to pre-built chord "anchor" profiles derived from phenomenological music research. The architecture is doc-driven: atomic markdown specs define each process, and changing a spec + re-running causes the corresponding code to be intelligently rewritten.

---

## Problem Statement

Embedding spaces are high-dimensional and opaque. Music is one of humanity's most expressive emotional interfaces. The question: can we "listen" to the emotional shape of a text by collapsing embedding space into musical chords that carry equivalent emotional weight?

The 7 diatonic chords of a major key are not arbitrary — each has an established, phenomenologically documented emotional character. If we can map text embeddings to chord embeddings via cosine similarity, we can sonify any text in a way that's emotionally meaningful rather than arbitrary.

---

## Proposed Solution

A three-layer pipeline:

```
[Text Input]
     ↓
[Python: sentence-transformers embed → cosine sim → chord selection]
     ↓
[ctcsound: CsoundPerformanceThread.scoreEvent() → synthesized audio]
```

The emotional bridge is the **chord anchor corpus**: for each of the 7 diatonic chords, a rich keyword/phrase document (the "keyword page") is embedded into a single dense vector. At runtime, any input text is embedded and compared against all 7 anchor vectors via cosine similarity. The closest chord plays.

---

## Technical Approach

### Architecture

**File layout:**

```
SonifyingEmbeddingsPlayground/
├── docs/
│   ├── plans/                   # this file and future plans
│   └── specs/                   # atomic infrastructure docs (doc-driven dev)
│       ├── 01-chord-corpus.md   # how keyword pages are authored and structured
│       ├── 02-anchor-embeddings.md  # how anchors are built from keyword pages
│       ├── 03-text-classifier.md    # how input text maps to a chord
│       ├── 04-csound-bridge.md      # Python↔Csound interface contract
│       └── 05-main-loop.md          # top-level behavior of the CLI/API
├── data/
│   └── chords/                  # keyword page per chord (markdown or JSON)
│       ├── I-tonic.md
│       ├── ii-supertonic.md
│       ├── iii-mediant.md
│       ├── IV-subdominant.md
│       ├── V-dominant.md
│       ├── vi-submediant.md
│       └── viidim-leading.md
├── src/
│   ├── anchor_builder.py        # reads data/chords/, builds anchor embeddings
│   ├── classifier.py            # embeds input text, cosine sim → chord
│   ├── csound_bridge.py         # ctcsound wrapper for chord playback
│   ├── chords.py                # chord definitions: MIDI, frequencies, metadata
│   └── main.py                  # CLI entry point
├── instruments/
│   └── pad.orc                  # Csound orchestra file
├── requirements.txt
└── CLAUDE.md                    # project constitution (doc-driven dev rules)
```

---

### Chord Definitions (C Major)

Fixed key: **C major**. Fixed voicing: **root-position triads, octave 4**.

| Numeral | Name | Notes | MIDI | Frequencies (Hz) | Emotional Anchor |
|---|---|---|---|---|---|
| I | C major | C4–E4–G4 | 60, 64, 67 | 261.63, 329.63, 392.00 | Stable, resolved, triumphant, home |
| ii | D minor | D4–F4–A4 | 62, 65, 69 | 293.66, 349.23, 440.00 | Gentle sadness, introspective, yearning |
| iii | E minor | E4–G4–B4 | 64, 67, 71 | 329.63, 392.00, 493.88 | Wistful, uncertain, ambiguous, questioning |
| IV | F major | F4–A4–C5 | 65, 69, 72 | 349.23, 440.00, 523.25 | Warm, uplifting, spiritual, longing departure |
| V | G major | G4–B4–D5 | 67, 71, 74 | 392.00, 493.88, 587.33 | Tension, anticipation, forward motion |
| vi | A minor | A4–C5–E5 | 69, 72, 76 | 440.00, 523.25, 659.25 | Melancholic, heartfelt, emotional sincerity |
| vii° | B dim | B4–D5–F5 | 71, 74, 77 | 493.88, 587.33, 698.46 | Dissonance, dread, urgency, instability |

---

### Phase 1: Chord Keyword Corpus (Data)

Build the emotional foundation. Each chord gets a **keyword page** — a rich prose/keyword document capturing how that chord *feels*, sourced from:

- **Kate Hevner Adjective Circle** (1935, updated Schubert 2003) — the canonical psychoacoustics reference. Maps 46 adjectives into 8 emotional clusters that map onto chord function. Source: https://pubmed.ncbi.nlm.nih.gov/12929763/
- **Empirical chord emotion research**: "Single chords convey distinct emotional qualities to both naïve and expert listeners" — https://www.researchgate.net/publication/266938286
- **Practitioner descriptions**: Tabletop Composer (https://www.tabletopcomposer.com/post/chord-relationships-and-emotion), Musiversal (https://musiversal.com/blog/write-emotional-chord-progressions)

**Keyword page structure for each chord:**

```markdown
# [Numeral]: [Name] — Emotional Keyword Page

## Core Adjectives (from Hevner clusters)
[15–25 adjectives, e.g.: stable, resolved, bright, confident, triumphant...]

## Extended Phrases
[10–15 short phrases describing the feeling, e.g.: "a deep breath after long effort",
"the moment of arriving home", "sunlight breaking through clouds"...]

## Atmospheric Contexts
[5–10 situational contexts: "end of a hard journey", "standing on solid ground"...]

## Contrasting with Neighbors
[Brief note on what distinguishes this chord from adjacent ones in feel]
```

**Anchor embedding construction:** Embed the entire keyword page as a **single concatenated string** → one 384-dimensional vector per chord. Do NOT average individual word embeddings (this loses semantic context).

**Validation step:** After building all 7 anchors, compute the full 7×7 pairwise cosine similarity matrix. If any pair exceeds 0.85 similarity, those two chord pages are too close and must be revised. Log the matrix for inspection.

**Deliverables:**
- `data/chords/*.md` — 7 keyword pages
- `docs/specs/01-chord-corpus.md` — spec describing authoring rules
- `docs/specs/02-anchor-embeddings.md` — spec describing embedding construction + validation

---

### Phase 2: Infrastructure Docs (Spec-Driven Development Setup)

This project uses **Spec-Driven Development (SDD)**: atomic markdown files in `docs/specs/` are the source of truth. Code is a compilation artifact. When a spec changes, the corresponding code is rewritten to match.

References:
- GitHub Spec-Driven Development guide: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-using-markdown-as-a-programming-language-when-building-with-ai/
- Addy Osmani's spec quality checklist: https://addyosmani.com/blog/good-spec/

**Each spec file contains:**
- `## Intent` — what this process does and why
- `## Inputs` — data types, sources
- `## Outputs` — return types, side effects
- `## Algorithm` — numbered steps (pseudocode-level)
- `## Constraints` — invariants, error conditions
- `## Example` — concrete input/output pair

**Specs to write:**
- `docs/specs/01-chord-corpus.md` — keyword page authoring rules
- `docs/specs/02-anchor-embeddings.md` — anchor construction and validation
- `docs/specs/03-text-classifier.md` — embedding + cosine sim → chord
- `docs/specs/04-csound-bridge.md` — Python↔Csound interface contract
- `docs/specs/05-main-loop.md` — top-level CLI/API behavior

**CLAUDE.md** at project root serves as the project constitution: describes the SDD pattern, file conventions, and how to trigger code regeneration.

**Deliverables:**
- `CLAUDE.md` — project constitution
- `docs/specs/01` through `docs/specs/05` — all five spec files

---

### Phase 3: Embedding Engine (text → chord)

**Library:** `sentence-transformers` with `all-MiniLM-L6-v2`
- 22M parameters, 384-dim output, runs sub-100ms on CPU
- Best local choice for semantic similarity tasks
- Install: `pip install sentence-transformers`
- Source: https://www.sbert.net/docs/sentence_transformer/pretrained_models.html

**`anchor_builder.py`:**
```python
# src/anchor_builder.py
# Reads data/chords/*.md, builds and optionally caches anchor embeddings
# Spec: docs/specs/02-anchor-embeddings.md
```
- Reads each chord's keyword page from `data/chords/`
- Encodes each as a single string → 384-dim tensor
- Computes and logs the 7×7 pairwise similarity matrix (validation)
- Saves anchor embeddings to `data/anchors.pt` (cached; regenerated when chord docs change)

**`classifier.py`:**
```python
# src/classifier.py
# Embeds input text, finds closest chord anchor via cosine sim
# Spec: docs/specs/03-text-classifier.md
```
- Loads cached anchors (or rebuilds if `data/anchors.pt` is stale vs. chord docs)
- `classify(text: str) -> ChordResult` where `ChordResult` contains:
  - `numeral: str` (e.g., "vi")
  - `name: str` (e.g., "A minor")
  - `score: float` (cosine similarity, 0–1)
  - `all_scores: dict[str, float]` (all 7 scores for transparency)
  - `midi_notes: list[int]` (e.g., [69, 72, 76])
  - `frequencies: list[float]`
- **Confidence threshold:** If `score < 0.15`, return `ChordResult` with `numeral="I"` as safe neutral fallback and flag `low_confidence=True`
- **Tie-breaking:** If top two chords are within 0.02 of each other, use functional harmony priority (I > IV > V > vi > ii > iii > vii°)

**`chords.py`:**
```python
# src/chords.py
# Static chord definitions, MIDI mappings, frequency tables
# Single source of truth for chord data
```

---

### Phase 4: Csound Integration (chord → sound)

**Library:** `ctcsound` + `CsoundPerformanceThread`
- Direct Python-to-Csound C API binding via ctypes
- Thread-safe chord triggering without blocking Python
- Official docs: https://csound.com/docs/ctcsound/ctcsound-API.html
- ⚠️ Csound 7 breaks backward compat with Csound 6 API — verify installed version before implementation. Alternative for Csound 7: `libcsound` (https://github.com/csound-plugins/libcsound)

**`csound_bridge.py`:**
```python
# src/csound_bridge.py
# Manages ctcsound lifecycle, exposes play_chord(chord_result: ChordResult)
# Spec: docs/specs/04-csound-bridge.md
```

Key design decisions:
- **Output target:** `-odac` (real-time to system audio device) as default; optionally `-o output.wav` for file capture
- **Chord parameters:** duration = 2.0s, amplitude = 0.4 (per note), envelope = linsegr 0→0.02→1→(dur-0.06)→0.8→0.04→0
- **Simultaneous notes:** all notes in a chord fire via separate `scoreEvent()` calls at `p2=0` (same start time)
- **Successive input behavior:** new chord interrupts previous (sends `turnoff` to all active instr 1 instances before triggering)
- **Console feedback:** always print `Playing [numeral] ([name]) — score: [x.xx]` before triggering audio

**`instruments/pad.orc` — Csound orchestra:**
```csound
sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1
    kenv  linsegr  0, 0.02, 1, p3 - 0.06, 0.8, 0.04, 0
    aout  oscili   p4 * kenv, p5
    outs  aout, aout
endin
```
> Note: `p4` = amplitude, `p5` = frequency in Hz

---

### Phase 5: CLI Interface + Extensibility Foundation

**`main.py`:**
```python
# src/main.py
# Interactive CLI: prompt → classify → play chord
# Spec: docs/specs/05-main-loop.md
```
- REPL loop: read text from stdin, classify, trigger Csound, print result, repeat
- `--file path` flag: read lines from a file, play one chord per line with a configurable delay
- `--dry-run` flag: print chord results without triggering audio (useful for testing without Csound installed)
- `Ctrl+C` / empty input: graceful shutdown (calls `pt.stop()`, `c.cleanup()`)

**Extensibility hooks (built in Phase 5, even if not fully implemented):**
- `ChordResult` is designed to compose: `[ChordResult, ChordResult, ...]` = a progression
- `classifier.py` exposes `classify_sequence(texts: list[str]) -> list[ChordResult]` for progression use
- `csound_bridge.py` has `play_progression(chords: list[ChordResult], tempo_bpm=80)` stub

---

## System-Wide Impact

### Interaction Graph

Text input → `classifier.classify()` → loads anchors from disk (or triggers `anchor_builder.rebuild()`) → `cosine_sim()` → `ChordResult` → `csound_bridge.play_chord()` → `CsoundPerformanceThread.scoreEvent()` × N (one per note in chord) → Csound audio thread → system audio output.

Spec change path: edit `docs/specs/*.md` → re-run `anchor_builder.py` (if chord corpus spec changed) → re-run code regeneration if algorithm spec changed → `data/anchors.pt` invalidated and rebuilt on next run.

### Error Propagation

- `sentence-transformers` encode failure → `classifier.py` raises `EmbeddingError`, caught in `main.py`, prints message, skips to next input
- `ctcsound` initialization failure → `csound_bridge.py` raises `CsoundInitError`, caught in `main.py`, falls back to `--dry-run` mode with warning
- Anchor file missing/stale → `anchor_builder.rebuild()` is triggered automatically
- Low confidence match → chord plays with `[LOW CONFIDENCE]` flag in console output

### State Lifecycle Risks

- `data/anchors.pt` can become stale if chord keyword pages are edited without clearing cache. Mitigation: store a hash of each keyword page alongside the anchor file; if hash mismatches on load, trigger rebuild.
- `CsoundPerformanceThread` must be explicitly stopped and joined on exit. Use `atexit` registration in `csound_bridge.py`.

---

## Acceptance Criteria

### Functional

- [ ] Given any string input, the system outputs a chord name and plays it within 500ms (on local hardware with sentence-transformers model pre-loaded)
- [ ] The 7 anchor embeddings have pairwise cosine similarities all below 0.85 (validated by `anchor_builder.py`)
- [ ] A curated test set of 10 (text, expected chord) pairs achieves ≥7/10 correct matches
- [ ] Changing a keyword page in `data/chords/` and re-running rebuilds anchors and changes classifications accordingly
- [ ] `--dry-run` mode works without Csound installed
- [ ] Console output always shows chord name, numeral, and similarity score

### Non-Functional

- [ ] Classification latency ≤100ms (excluding Csound audio synthesis)
- [ ] No audio overlap: new chord cleanly interrupts previous
- [ ] All 5 spec files exist in `docs/specs/` with intent/inputs/outputs/algorithm/constraints/example sections
- [ ] `CLAUDE.md` exists and describes the doc-driven development pattern

### Extensibility

- [ ] `classify_sequence()` exists and returns `list[ChordResult]` for progression groundwork
- [ ] `play_progression()` stub exists in `csound_bridge.py`
- [ ] `ChordResult` is a dataclass/named tuple that composes cleanly into lists

---

## Alternative Approaches Considered

| Approach | Why Rejected |
|---|---|
| Fine-tuned text classifier (trained on emotion labels) | Requires labeled training data; overkill for 7 classes; no flexibility to change chord meanings by editing a doc |
| MIDI output instead of Csound | Loses the ability to design custom timbres and soundscapes; Csound is required for future soundscape mode |
| Averaging individual keyword embeddings (instead of full-page embed) | Loses syntactic and contextual relationships between keywords; empirically produces less discriminative anchors |
| OpenAI `ada-002` embeddings | Better accuracy but requires API key, network, and cost; `all-MiniLM-L6-v2` is sufficient for 7-class discrimination with rich keyword pages |
| OSC (separate Python + Csound processes) | Adds complexity; ctcsound same-process integration is simpler for MVP; OSC can be added later if hot-reload of Python logic is needed |

---

## Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `sentence-transformers` | ≥2.6 | Text embeddings |
| `torch` | ≥2.0 | Tensor ops for cosine similarity |
| `ctcsound` / `libcsound` | match Csound version | Python↔Csound bridge |
| Csound | 6.18 or 7.x | Audio synthesis engine |
| Python | ≥3.10 | Runtime |

**Pre-requisite:** Csound must be installed separately (not pip-installable). macOS: `brew install csound`. Verify version to choose ctcsound vs libcsound.

---

## Success Metrics

1. **Semantic coherence:** 7/10 on the curated test set
2. **Anchor separation:** All pairwise similarities < 0.85
3. **Latency:** Classification in ≤100ms (warm start)
4. **Doc coverage:** All 5 specs written and matched by corresponding code
5. **Subjective resonance:** Playing the output while reading the input text feels emotionally consistent

---

## Future Considerations

- **Embedding model comparison**: Once the keyword pages and a 10-example test set exist, run a side-by-side benchmark across models to find the quality/speed tradeoff that works for this project:

  | Model | Dim | Local? | Expected strength |
  |---|---|---|---|
  | `all-MiniLM-L6-v2` | 384 | ✅ | Baseline (fast) |
  | `all-mpnet-base-v2` | 768 | ✅ | Better adjacent-chord separation |
  | `Qwen3-Embedding-0.6B` | 1024 | ✅ | MTEB SOTA (2025), instruction-aware (test explicitly with affect instruction prefix: `"Instruct: Represent this text by its emotional character for matching to a musical chord.\nQuery: "`) |
  | `text-embedding-3-small` | 1536 | ❌ API | Best nuance for poetic/literary text |

  Focus evaluation on the **hard adjacent-chord pairs**: I vs. IV, vi vs. ii, iii vs. vii°. The model is a one-line swap in `docs/specs/02-anchor-embeddings.md` — architecture already supports this.

- **Chord progressions**: `classify_sequence()` takes a list of texts (e.g., lines of a poem) and returns a chord progression. `play_progression()` sequences them with configurable tempo.
- **Soundscape mode**: All chords from a document are layered as pads rather than played in sequence. Requires a mixing/blend layer in Csound.
- **Embedding influence**: The doc-driven pattern means changing `docs/specs/02-anchor-embeddings.md` can change the embedding strategy (e.g., switch from sentence-level to multi-anchor per chord) and the code will be regenerated to match.
- **Poetry Foundation integration**: Feed poem lines through `classify_sequence()` for a per-stanza chord progression.
- **Per-word arpeggio mode**: Map individual words to individual notes (not chords), forming arpeggios from sentences.

---

## Sources & References

### Internal

- `mvp.md` — original feature spec
- `notes.md` — exploratory brainstorming with key architectural constraints

### Embeddings & Classification

- sentence-transformers pretrained models: https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
- `all-MiniLM-L6-v2` on Hugging Face: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- Semantic search tutorial: https://sbert.net/examples/applications/semantic-search/README.html

### Chord Emotion Research

- Hevner Adjective Circle (Schubert 2003 update): https://pubmed.ncbi.nlm.nih.gov/12929763/
- "Single chords convey distinct emotional qualities": https://www.researchgate.net/publication/266938286
- Music emotion datasets collection: https://github.com/juansgomez87/datasets_emotion
- EMOPIA dataset (valence-arousal chord labels): https://archives.ismir.net/ismir2021/paper/000039.pdf
- Tabletop Composer chord emotion guide: https://www.tabletopcomposer.com/post/chord-relationships-and-emotion
- Musiversal emotional chord progressions: https://musiversal.com/blog/write-emotional-chord-progressions

### Csound Integration

- ctcsound API: https://csound.com/docs/ctcsound/ctcsound-API.html
- ctcsound CsoundPerformanceThread: https://csound.com/docs/ctcsound/ctcsound-PT.html
- ctcsound GitHub: https://github.com/csound/ctcsound
- Real-time score events (Csound Journal): https://csoundjournal.com/issue14/realtimeCsoundPython.html
- libcsound (Csound 7 compatible): https://github.com/csound-plugins/libcsound
- FLOSS Csound manual (OSC): https://flossmanual.csound.com/other-communication/open-sound-control

### Spec-Driven Development

- GitHub SDD guide: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-using-markdown-as-a-programming-language-when-building-with-ai/
- GitHub Spec Kit: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- Addy Osmani's spec quality guide: https://addyosmani.com/blog/good-spec/
- Markdown-Driven Development (DEV Community): https://dev.to/simbo1905/augmented-intelligence-ai-coding-using-markdown-driven-development-pg5
