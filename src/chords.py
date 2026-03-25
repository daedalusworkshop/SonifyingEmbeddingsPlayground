"""
Chord definitions for C major diatonic chords.
Single source of truth for all chord data — no other file hardcodes chord info.
"""

from dataclasses import dataclass, field


@dataclass
class ChordDef:
    numeral: str
    name: str
    midi_notes: list[int]
    keyword_file: str  # relative to data/chords/

    @property
    def frequencies(self) -> list[float]:
        return [midi_to_freq(n) for n in self.midi_notes]


def midi_to_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


# Canonical order — must match row order in data/anchors.pt
CHORDS: list[ChordDef] = [
    ChordDef("I",    "C major",    [60, 64, 67], "I-tonic.md"),
    ChordDef("ii",   "D minor",    [62, 65, 69], "ii-supertonic.md"),
    ChordDef("iii",  "E minor",    [64, 67, 71], "iii-mediant.md"),
    ChordDef("IV",   "F major",    [65, 69, 72], "IV-subdominant.md"),
    ChordDef("V",    "G major",    [67, 71, 74], "V-dominant.md"),
    ChordDef("vi",   "A minor",    [69, 72, 76], "vi-submediant.md"),
    ChordDef("vii°", "B diminished", [71, 74, 77], "viidim-leading.md"),
]

# Tie-breaking priority: index = priority (lower = higher priority)
TIE_BREAK_ORDER = ["I", "IV", "V", "vi", "ii", "iii", "vii°"]

CHORD_BY_NUMERAL: dict[str, ChordDef] = {c.numeral: c for c in CHORDS}


@dataclass
class ChordResult:
    numeral: str
    name: str
    score: float
    all_scores: dict[str, float]
    midi_notes: list[int]
    frequencies: list[float]
    low_confidence: bool = False
