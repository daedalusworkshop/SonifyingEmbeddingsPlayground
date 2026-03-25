"""
Embeds input text and classifies it to the closest diatonic chord.
Spec: docs/specs/03-text-classifier.md
"""

import torch
from sentence_transformers import SentenceTransformer, util

import anchor_builder
from chords import CHORDS, TIE_BREAK_ORDER, ChordResult

MODEL_NAME = "all-MiniLM-L6-v2"
CONFIDENCE_THRESHOLD = 0.15
TIE_TOLERANCE = 0.02


class Classifier:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.anchors: torch.Tensor = anchor_builder.build()

    def classify(self, text: str) -> ChordResult:
        if not text.strip():
            chord = CHORDS[0]
            return ChordResult(
                numeral=chord.numeral,
                name=chord.name,
                score=0.0,
                all_scores={c.numeral: 0.0 for c in CHORDS},
                midi_notes=chord.midi_notes,
                frequencies=chord.frequencies,
                low_confidence=True,
            )

        text_emb = self.model.encode(text, convert_to_tensor=True)
        scores_tensor = util.cos_sim(text_emb, self.anchors)[0]
        scores = [float(scores_tensor[i]) for i in range(len(CHORDS))]
        all_scores = {CHORDS[i].numeral: scores[i] for i in range(len(CHORDS))}

        best_score = max(scores)
        low_confidence = best_score < CONFIDENCE_THRESHOLD

        if low_confidence:
            best_idx = 0  # fallback to I
        else:
            # Collect all indices within tie tolerance of the best
            candidates = [i for i, s in enumerate(scores) if best_score - s <= TIE_TOLERANCE]
            if len(candidates) == 1:
                best_idx = candidates[0]
            else:
                # Break tie using functional harmony priority
                priority = {n: i for i, n in enumerate(TIE_BREAK_ORDER)}
                best_idx = min(candidates, key=lambda i: priority.get(CHORDS[i].numeral, 99))

        chord = CHORDS[best_idx]
        return ChordResult(
            numeral=chord.numeral,
            name=chord.name,
            score=best_score,
            all_scores=all_scores,
            midi_notes=chord.midi_notes,
            frequencies=chord.frequencies,
            low_confidence=low_confidence,
        )

    def classify_sequence(self, texts: list[str]) -> list[ChordResult]:
        return [self.classify(t) for t in texts]
