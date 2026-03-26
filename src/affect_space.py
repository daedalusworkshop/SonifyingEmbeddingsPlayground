"""
Affect space for chord classification.

Five emotional dimensions, each 0.0–1.0, that together cleanly separate
the 7 diatonic chords. Chord coordinates are either loaded from
data/chord_coords.json (written by scripts/place_chords.py) or fall back
to DEFAULT_COORDS below.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

COORDS_PATH = Path("data/chord_coords.json")

# The five affect axes, in order. Indices matter — vectors must match this order.
DIMENSIONS = [
    "valence",       # 0.0 = dark/unpleasant  →  1.0 = bright/pleasant
    "arousal",       # 0.0 = still/calm       →  1.0 = urgent/kinetic
    "tension",       # 0.0 = resolved         →  1.0 = unresolved
    "direction",     # 0.0 = retrospective    →  1.0 = anticipatory
    "expressiveness",# 0.0 = interior/private →  1.0 = raw/open
]

N_DIMS = len(DIMENSIONS)

# Baseline coordinates — placed by LLM reasoning about functional harmony.
# These are used as fallback when chord_coords.json is absent.
# Run scripts/place_chords.py to regenerate with a different music theory.
DEFAULT_COORDS: dict[str, list[float]] = {
    #         valence  arousal  tension  direction  expressiveness
    "I":    [  0.85,    0.20,    0.05,    0.15,      0.25  ],
    "ii":   [  0.45,    0.35,    0.45,    0.70,      0.40  ],
    "iii":  [  0.40,    0.25,    0.30,    0.35,      0.15  ],
    "IV":   [  0.75,    0.30,    0.20,    0.50,      0.65  ],
    "V":    [  0.55,    0.80,    0.90,    0.90,      0.70  ],
    "vi":   [  0.30,    0.25,    0.25,    0.20,      0.75  ],
    "vii°": [  0.20,    0.85,    0.95,    0.80,      0.80  ],
}


def load_coords() -> dict[str, list[float]]:
    """Load chord coordinates from disk, falling back to DEFAULT_COORDS."""
    if COORDS_PATH.exists():
        data = json.loads(COORDS_PATH.read_text())
        return data["coords"]
    return DEFAULT_COORDS


def coords_matrix(numerals: list[str]) -> list[list[float]]:
    """Return coordinate vectors in the given numeral order."""
    coords = load_coords()
    return [coords[n] for n in numerals]


def euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def nearest_chord(query_vec: list[float], numerals: list[str]) -> tuple[str, float]:
    """
    Return (numeral, distance) of the chord nearest to query_vec.
    Lower distance = better match.
    """
    coords = load_coords()
    best_numeral = numerals[0]
    best_dist = float("inf")
    for n in numerals:
        d = euclidean_distance(query_vec, coords[n])
        if d < best_dist:
            best_dist = d
            best_numeral = n
    return best_numeral, best_dist


def all_distances(query_vec: list[float], numerals: list[str]) -> dict[str, float]:
    """Return distance from query_vec to every chord."""
    coords = load_coords()
    return {n: euclidean_distance(query_vec, coords[n]) for n in numerals}
