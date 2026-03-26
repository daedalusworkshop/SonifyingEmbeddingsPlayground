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
    ChordDef("I",    "C major",    [48, 52, 55], "I-tonic.md"),
    ChordDef("ii",   "D minor",    [50, 53, 57], "ii-supertonic.md"),
    ChordDef("iii",  "E minor",    [52, 55, 59], "iii-mediant.md"),
    ChordDef("IV",   "F major",    [53, 57, 60], "IV-subdominant.md"),
    ChordDef("V",    "G major",    [55, 59, 62], "V-dominant.md"),
    ChordDef("vi",   "A minor",    [57, 60, 64], "vi-submediant.md"),
    ChordDef("vii°", "B diminished", [59, 62, 65], "viidim-leading.md"),
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
