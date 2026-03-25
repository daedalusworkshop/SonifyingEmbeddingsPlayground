# Spec 01: Chord Corpus

## Intent
Define and maintain the emotional keyword pages that serve as the ground truth for each chord's emotional character. These pages are the primary determinant of classification quality — their richness and distinctiveness matter more than model choice.

## Inputs
- Human authorship and music phenomenology research (Hevner Adjective Circle, empirical chord emotion studies)

## Outputs
- 7 markdown files in `data/chords/`, one per diatonic chord in C major
- Filenames: `I-tonic.md`, `ii-supertonic.md`, `iii-mediant.md`, `IV-subdominant.md`, `V-dominant.md`, `vi-submediant.md`, `viidim-leading.md`

## Structure of Each Keyword Page
Each file must contain these four sections:
1. **Core Adjectives** — 20–30 single words or short phrases describing the emotional quality
2. **Extended Phrases** — 10–15 complete-phrase descriptions (sentence fragments or full sentences)
3. **Atmospheric Contexts** — 5–10 situational or sensory descriptions
4. **Contrasting with Neighbors** — a short paragraph distinguishing this chord from the adjacent ones that are most likely to be confused with it

## Constraints
- Pages must be emotionally distinctive, not music-theoretically descriptive (no "major third", "subdominant function")
- Target reading level: accessible, evocative, not academic
- After anchors are built, the pairwise cosine similarity matrix must show all pairs < 0.85
- If any pair exceeds 0.85, revise the more similar of the two pages to increase distinctiveness

## Example
See `data/chords/vi-submediant.md` as the reference for emotional depth and phrase variety.
