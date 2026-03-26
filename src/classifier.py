"""
Embeds input text and classifies it to the closest diatonic chord.
Spec: docs/specs/03-text-classifier.md
"""

import torch
from sentence_transformers import SentenceTransformer, util

import anchor_builder
from chords import CHORDS, ChordResult

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
INSTRUCTION = (
    "Instruct: Represent this text by its emotional and affective character "
    "for matching to a musical chord.\nQuery: "
)
CONFIDENCE_THRESHOLD = 0.40  # Qwen scores are higher; raise threshold accordingly
TEMPERATURE = 0.05  # lower → closer to argmax; higher → more harmonic variety


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

        text_emb = self.model.encode(INSTRUCTION + text, convert_to_tensor=True, normalize_embeddings=True)
        scores_tensor = util.cos_sim(text_emb, self.anchors)[0]
        scores = [float(scores_tensor[i]) for i in range(len(CHORDS))]
        all_scores = {CHORDS[i].numeral: scores[i] for i in range(len(CHORDS))}

        best_score = max(scores)
        low_confidence = best_score < CONFIDENCE_THRESHOLD

        # Temperature sampling: ties and ambiguous cases produce natural harmonic variety
        probs = torch.softmax(scores_tensor / TEMPERATURE, dim=0)
        chosen_idx = int(torch.multinomial(probs, 1).item())

        chord = CHORDS[chosen_idx]
        return ChordResult(
            numeral=chord.numeral,
            name=chord.name,
            score=scores[chosen_idx],
            all_scores=all_scores,
            midi_notes=chord.midi_notes,
            frequencies=chord.frequencies,
            low_confidence=low_confidence,
        )

    def classify_sequence(self, texts: list[str]) -> list[ChordResult]:
        return [self.classify(t) for t in texts]
