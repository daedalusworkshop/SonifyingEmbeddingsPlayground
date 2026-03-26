"""
Place diatonic chords in the 5-dim affect space using an LLM.

Usage:
    python scripts/place_chords.py --theory "functional harmony in C major"
    python scripts/place_chords.py --theory "jazz harmony, modal color" --model claude-haiku-4-5-20251001

The LLM is asked to rate each chord on 5 axes (0.0–1.0).
Output is written to data/chord_coords.json and printed as a table.
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

# Allow running from repo root or scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from affect_space import DIMENSIONS
from chords import CHORDS

DATA_DIR = Path(__file__).parent.parent / "data"
OUT_PATH = DATA_DIR / "chord_coords.json"

SYSTEM_PROMPT = """\
You are a music theorist and psychoacoustics expert. You rate musical chords on \
emotional affect dimensions with precision and consistency. Always respond with \
valid JSON only — no explanation, no markdown."""

RATING_PROMPT = """\
Theory context: {theory}

Rate the following chord on each affect dimension, using float values from 0.0 to 1.0.

Chord: {numeral} ({name})

Dimensions:
- valence: 0.0 = dark/unpleasant, 1.0 = bright/pleasant
- arousal: 0.0 = still/calm, 1.0 = urgent/kinetic
- tension: 0.0 = fully resolved, 1.0 = highly unresolved
- direction: 0.0 = retrospective/backward-looking, 1.0 = anticipatory/forward-leaning
- expressiveness: 0.0 = interior/private, 1.0 = raw/open

Respond with exactly this JSON structure:
{{
  "valence": <float>,
  "arousal": <float>,
  "tension": <float>,
  "direction": <float>,
  "expressiveness": <float>
}}"""


def place_chord(client: anthropic.Anthropic, numeral: str, name: str, theory: str, model: str) -> list[float]:
    prompt = RATING_PROMPT.format(theory=theory, numeral=numeral, name=name)
    response = client.messages.create(
        model=model,
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    data = json.loads(raw)
    return [float(data[dim]) for dim in DIMENSIONS]


def print_table(theory: str, coords: dict[str, list[float]]) -> None:
    header = f"  {'Chord':<8}" + "".join(f"  {d[:6]:>8}" for d in DIMENSIONS)
    print(f"\nTheory: {theory}")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for numeral, vec in coords.items():
        row = f"  {numeral:<8}" + "".join(f"  {v:>8.3f}" for v in vec)
        print(row)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Place diatonic chords in affect space via LLM.")
    parser.add_argument("--theory", default="functional harmony in C major",
                        help="Music theory context for the LLM (default: functional harmony in C major)")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001",
                        help="Anthropic model to use")
    parser.add_argument("--offline", action="store_true",
                        help="Skip LLM call; write DEFAULT_COORDS from affect_space.py")
    args = parser.parse_args()

    coords: dict[str, list[float]] = {}

    if args.offline:
        from affect_space import DEFAULT_COORDS
        coords = dict(DEFAULT_COORDS)
        print(f"Offline mode — using DEFAULT_COORDS from affect_space.py")
    else:
        client = anthropic.Anthropic()
        print(f"Placing {len(CHORDS)} chords using theory: \"{args.theory}\"")
        for chord in CHORDS:
            print(f"  → {chord.numeral} ({chord.name})...", end=" ", flush=True)
            try:
                vec = place_chord(client, chord.numeral, chord.name, args.theory, args.model)
                coords[chord.numeral] = vec
                print("✓")
            except Exception as e:
                print(f"✗ ({e})")
                sys.exit(1)

    print_table(args.theory, coords)

    DATA_DIR.mkdir(exist_ok=True)
    payload = {"theory": args.theory, "model": args.model, "coords": coords}
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Saved → {OUT_PATH}")


if __name__ == "__main__":
    main()
