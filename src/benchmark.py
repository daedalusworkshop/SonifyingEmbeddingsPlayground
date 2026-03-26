"""
Playable benchmark — runs each test case, plays the predicted chord, waits for keypress.
Press Enter to advance, 'r' to replay, 'q' to quit.

Usage:
  python3.14 src/benchmark.py          # interactive playback
  python3.14 src/benchmark.py --silent  # no audio, just print results
"""

import sys
import re
import time
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer, util

sys.path.insert(0, str(Path(__file__).parent))
from chords import CHORDS, CHORD_BY_NUMERAL

ROOT = Path(__file__).parent.parent
CHORDS_DIR = ROOT / "data" / "chords"

INSTRUCTION = (
    "Instruct: Represent this text by its emotional and affective character "
    "for matching to a musical chord.\nQuery: "
)

TESTS = [
    # Clear cases
    ("the sun came out and everything felt whole",         "I",    "clear"),
    ("I miss her so much it physically hurts",            "vi",   "clear"),
    ("something terrible is about to happen",             "vii°", "clear"),
    ("I can feel it building, almost there",              "V",    "clear"),
    ("I want to be better, I am reaching for something",  "IV",   "clear"),
    # Hard adjacent-chord cases
    ("a quiet sadness, held privately inside",            "ii",   "hard: ii vs vi"),
    ("I feel at peace, everything has settled",           "I",    "hard: I vs IV"),
    ("longing for something I cannot name",               "IV",   "hard: IV vs vi"),
    ("a vague unease, something unnamed",                 "iii",  "hard: iii vs vii°"),
    ("everything is falling apart",                       "vii°", "hard: vii° vs V"),
]


def strip_markdown(text: str) -> str:
    text = re.sub(r"^#+\s.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s", "", text, flags=re.MULTILINE)
    return text.strip()


def build_anchors(model):
    texts = [INSTRUCTION + strip_markdown((CHORDS_DIR / c.keyword_file).read_text()) for c in CHORDS]
    return model.encode(texts, convert_to_tensor=True, normalize_embeddings=True)


def classify(text, anchors, model):
    emb = model.encode(INSTRUCTION + text, convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(emb, anchors)[0]
    best_idx = int(scores.argmax())
    return CHORDS[best_idx], float(scores[best_idx])


def play(bridge, chord_def):
    from chords import ChordResult
    result = ChordResult(
        numeral=chord_def.numeral,
        name=chord_def.name,
        score=0.0,
        all_scores={},
        midi_notes=chord_def.midi_notes,
        frequencies=chord_def.frequencies,
    )
    bridge._pt.inputMessage("i -1 0 0")  # stop previous
    for freq in result.frequencies:
        bridge._pt.scoreEvent(False, "i", [1, 0, 2.5, 0.4, freq])


def main():
    silent = "--silent" in sys.argv

    bridge = None
    if not silent:
        try:
            from csound_bridge import CsoundBridge, CsoundNotAvailableError
            bridge = CsoundBridge()
        except Exception as e:
            print(f"⚠️  Audio unavailable ({e}), running silent.")

    print("Loading model...")
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    anchors = build_anchors(model)

    # Pre-classify everything
    results = [classify(text, anchors, model) for text, *_ in TESTS]

    print(f"\n{'─'*70}")
    print(f"  Playable benchmark — {len(TESTS)} test cases")
    if bridge:
        print("  Enter to advance · r = replay · q = quit")
    print(f"{'─'*70}\n")

    correct = 0
    i = 0
    while i < len(TESTS):
        text, expected, difficulty = TESTS[i]
        pred_chord, score = results[i]
        ok = "✓" if pred_chord.numeral == expected else "✗"
        if pred_chord.numeral == expected:
            correct += 1

        print(f"  [{i+1}/{len(TESTS)}] {ok}  {difficulty}")
        print(f"  \"{text}\"")
        print(f"  Expected: {expected:<5}  Got: {pred_chord.numeral} ({pred_chord.name})  score: {score:.2f}")

        if bridge:
            play(bridge, pred_chord)
            cmd = input("\n  [Enter] next  [r] replay  [q] quit  > ").strip().lower()
            print()
            if cmd == "q":
                break
            elif cmd == "r":
                continue  # don't increment, replay same
        else:
            print()

        i += 1

    print(f"{'─'*70}")
    print(f"  Result: {correct}/{len(TESTS)} correct\n")

    if bridge:
        bridge.close()


if __name__ == "__main__":
    main()
