"""
Maps input text to a 5-dim affect vector for chord classification.

Two implementations share a common interface:

    mapper.map(text: str) -> list[float]  # returns [valence, arousal, tension, direction, expressiveness]

LexiconMapper  — uses VADER (NLTK) + keyword-based projection. Zero latency, no API calls.
PromptedMapper — asks Claude to rate the text on each axis. More accurate, adds latency.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from affect_space import DIMENSIONS, N_DIMS


# ---------------------------------------------------------------------------
# LexiconMapper
# ---------------------------------------------------------------------------

# Per-word overrides for the three axes VADER doesn't directly provide.
# Format: word → [tension_delta, direction_delta, expressiveness_delta]
# Values are added to a neutral baseline of 0.5 before clamping to [0, 1].
_KEYWORD_OVERRIDES: dict[str, list[float]] = {
    # --- HIGH TENSION / vii° ---
    "tension":      [ 0.45,  0.30,  0.20],
    "unresolved":   [ 0.45,  0.20,  0.10],
    "dissonant":    [ 0.45,  0.10,  0.10],
    "unstable":     [ 0.40,  0.10,  0.15],
    "broken":       [ 0.40,  0.05,  0.20],
    "wrong":        [ 0.35,  0.00,  0.15],
    "vertigo":      [ 0.40,  0.10,  0.25],
    "shifting":     [ 0.30,  0.05,  0.15],
    "discomfort":   [ 0.35,  0.05,  0.20],
    "sharp":        [ 0.30,  0.05,  0.25],
    "falls":        [ 0.25, -0.10,  0.15],
    "apart":        [ 0.30, -0.10,  0.20],
    "collapse":     [ 0.40,  0.05,  0.25],
    "dark":         [ 0.20,  0.05,  0.15],
    "chaotic":      [ 0.40,  0.05,  0.30],
    # --- HIGH TENSION / V (anticipatory) ---
    "urgent":       [ 0.35,  0.40,  0.30],
    "anticipation": [ 0.35,  0.45,  0.20],
    "anxious":      [ 0.35,  0.10,  0.10],
    "restless":     [ 0.30,  0.20,  0.20],
    "building":     [ 0.30,  0.40,  0.10],
    "coiled":       [ 0.35,  0.35,  0.15],
    "about":        [ 0.20,  0.30,  0.00],
    "imminent":     [ 0.30,  0.40,  0.10],
    "breath":       [ 0.25,  0.30,  0.20],
    "plunge":       [ 0.35,  0.35,  0.30],
    "energy":       [ 0.25,  0.25,  0.25],
    "ready":        [ 0.20,  0.30,  0.15],
    "release":      [ 0.15,  0.20,  0.25],
    "moment":       [ 0.10,  0.20,  0.00],
    # --- RESOLVED / tonic ---
    "resolved":     [-0.45, -0.35, -0.20],
    "settled":      [-0.40, -0.30, -0.25],
    "arrived":      [-0.35, -0.35, -0.10],
    "complete":     [-0.35, -0.35, -0.15],
    "finished":     [-0.35, -0.40, -0.15],
    "home":         [-0.40, -0.40, -0.15],
    "still":        [-0.30, -0.40, -0.25],
    "grounded":     [-0.35, -0.35, -0.20],
    "whole":        [-0.30, -0.30, -0.15],
    # --- ANTICIPATORY / forward (V / ii) ---
    "coming":       [ 0.10,  0.35,  0.05],
    "before":       [ 0.15,  0.30,  0.00],
    "soon":         [ 0.10,  0.35,  0.05],
    "forward":      [ 0.05,  0.40,  0.10],
    "toward":       [ 0.05,  0.35,  0.10],
    "reaching":     [ 0.15,  0.30,  0.15],
    "seeking":      [ 0.10,  0.30,  0.10],
    # --- YEARNING / ii ---
    "longing":      [ 0.15,  0.25,  0.20],
    "curious":      [ 0.10,  0.20,  0.10],
    "wandering":    [ 0.10,  0.15,  0.10],
    "hopeful":      [ 0.10,  0.25,  0.10],
    "question":     [ 0.15,  0.15,  0.10],
    "yearning":     [ 0.20,  0.25,  0.20],
    "uncertain":    [ 0.15,  0.10,  0.05],
    "searching":    [ 0.10,  0.20,  0.15],
    # --- RETROSPECTIVE / backward (vi) ---
    "past":         [-0.05, -0.35,  0.10],
    "looking":      [-0.05, -0.20,  0.05],
    "back":         [-0.05, -0.35,  0.10],
    "memory":       [-0.05, -0.35,  0.10],
    "nostalgic":    [-0.05, -0.40,  0.20],
    "nostalgically":[-0.05, -0.40,  0.20],
    "gone":         [-0.05, -0.35,  0.20],
    "passed":       [-0.05, -0.35,  0.15],
    "wistful":      [-0.05, -0.35,  0.25],
    "bittersweet":  [ 0.05, -0.20,  0.35],
    "sadness":      [ 0.05, -0.15,  0.30],
    "missing":      [ 0.05, -0.25,  0.30],
    "ache":         [ 0.10, -0.10,  0.35],
    "autumn":       [-0.05, -0.25,  0.20],
    # --- OPEN / expressive (IV / vi) ---
    "open":         [-0.05, -0.05,  0.35],
    "expansive":    [-0.05,  0.05,  0.35],
    "vast":         [-0.05,  0.00,  0.35],
    "raw":          [ 0.10,  0.15,  0.40],
    "exposed":      [ 0.10,  0.05,  0.40],
    "wide":         [-0.05, -0.05,  0.30],
    "breathe":      [-0.10, -0.10,  0.25],
    "outside":      [-0.05,  0.10,  0.30],
    "sky":          [-0.05,  0.05,  0.25],
    "landscape":    [-0.10,  0.05,  0.30],
    "generous":     [-0.05,  0.05,  0.30],
    "morning":      [-0.05,  0.20,  0.25],
    # --- INTERIOR / private (iii) ---
    "inward":       [ 0.00, -0.15, -0.35],
    "interior":     [ 0.00, -0.10, -0.30],
    "private":      [ 0.00, -0.10, -0.30],
    "quiet":        [-0.10, -0.20, -0.25],
    "hushed":       [-0.05, -0.20, -0.25],
    "internal":     [ 0.00, -0.15, -0.30],
    "reverie":      [-0.05, -0.20, -0.30],
    "dreaming":     [-0.05, -0.20, -0.30],
    "suspended":    [ 0.10, -0.15, -0.20],
    "between":      [ 0.05, -0.05, -0.15],
}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


class LexiconMapper:
    """
    Maps text to a 5-dim affect vector using VADER + keyword overrides.

    VADER provides compound sentiment → valence, intensity → arousal.
    Tension, direction, and expressiveness are projected from keyword matching.
    """

    def __init__(self) -> None:
        from nltk.sentiment import SentimentIntensityAnalyzer
        self._sia = SentimentIntensityAnalyzer()

    def map(self, text: str) -> list[float]:
        if not text.strip():
            return [0.5] * N_DIMS

        scores = self._sia.polarity_scores(text)
        compound = scores["compound"]  # -1.0 to +1.0

        # valence: remap compound from [-1, 1] to [0, 1]
        valence = (compound + 1.0) / 2.0

        # arousal: driven by sentiment intensity (pos + neg components)
        intensity = scores["pos"] + scores["neg"]
        arousal = _clamp(0.3 + intensity * 0.7)

        # tension, direction, expressiveness: start at neutral 0.5, apply keyword deltas
        tension = 0.5
        direction = 0.5
        expressiveness = 0.5

        words = re.findall(r"[a-z']+", text.lower())
        for word in words:
            if word in _KEYWORD_OVERRIDES:
                td, dd, ed = _KEYWORD_OVERRIDES[word]
                tension += td
                direction += dd
                expressiveness += ed

        return [
            _clamp(valence),
            _clamp(arousal),
            _clamp(tension),
            _clamp(direction),
            _clamp(expressiveness),
        ]


# ---------------------------------------------------------------------------
# PromptedMapper
# ---------------------------------------------------------------------------

_PROMPTED_SYSTEM = """\
You are a psychoacoustics expert. You rate text passages on emotional affect \
dimensions with precision. Always respond with valid JSON only — no explanation, \
no markdown fences."""

_PROMPTED_TEMPLATE = """\
Rate the emotional affect of the following text on each dimension (0.0–1.0):

Text: "{text}"

Dimensions:
- valence: 0.0 = dark/unpleasant, 1.0 = bright/pleasant
- arousal: 0.0 = still/calm, 1.0 = urgent/kinetic
- tension: 0.0 = fully resolved/at rest, 1.0 = highly unresolved/tense
- direction: 0.0 = retrospective/backward-looking, 1.0 = anticipatory/forward-leaning
- expressiveness: 0.0 = interior/private/contained, 1.0 = raw/open/exposed

Respond with exactly this JSON:
{{"valence": <float>, "arousal": <float>, "tension": <float>, "direction": <float>, "expressiveness": <float>}}"""


class PromptedMapper:
    """
    Maps text to a 5-dim affect vector by prompting an LLM.
    Falls back to LexiconMapper if the API call fails.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = model
        self._fallback = LexiconMapper()

    def map(self, text: str) -> list[float]:
        if not text.strip():
            return [0.5] * N_DIMS
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=128,
                system=_PROMPTED_SYSTEM,
                messages=[{"role": "user", "content": _PROMPTED_TEMPLATE.format(text=text)}],
            )
            raw = response.content[0].text.strip()
            data = json.loads(raw)
            return [_clamp(float(data[dim])) for dim in DIMENSIONS]
        except Exception:
            return self._fallback.map(text)
