"""
Interactive CLI: type text, hear its chord.
Spec: docs/specs/05-main-loop.md

Usage:
  python src/main.py                      # REPL mode
  python src/main.py --file poem.txt      # file mode
  python src/main.py --dry-run            # no audio
  python src/main.py --file poem.txt --delay 3.0
"""

import argparse
import sys
import time
from pathlib import Path

# Allow running from project root or from src/
sys.path.insert(0, str(Path(__file__).parent))

from classifier import AffectClassifier, Classifier
from csound_bridge import CsoundBridge, CsoundNotAvailableError


def parse_args():
    p = argparse.ArgumentParser(description="Sonifying Embeddings — text to chord")
    p.add_argument("--file", type=Path, help="Read lines from file (one chord per line)")
    p.add_argument("--dry-run", action="store_true", help="Print results without audio")
    p.add_argument("--delay", type=float, default=2.5, help="Seconds between chords in file mode")
    p.add_argument("--affect-space", action="store_true", help="Use affect space classifier instead of embedding classifier")
    p.add_argument("--mapper", default="lexicon", choices=["lexicon", "prompted"], help="Query mapper for affect space mode (default: lexicon)")
    return p.parse_args()


def main():
    args = parse_args()

    # Init classifier
    if args.affect_space:
        print(f"Loading affect space classifier (mapper: {args.mapper})...")
        classifier = AffectClassifier(mapper=args.mapper)
    else:
        print("Loading model and anchors...")
        classifier = Classifier()

    # Init audio
    bridge = None
    if not args.dry_run:
        try:
            bridge = CsoundBridge()
        except CsoundNotAvailableError as e:
            print(f"⚠️  Csound unavailable ({e}), running in dry-run mode.")

    def process(text: str) -> None:
        result = classifier.classify(text)
        if bridge:
            bridge.play_chord(result)
        else:
            confidence_tag = "  [LOW CONFIDENCE]" if result.low_confidence else ""
            print(f"[dry-run] {result.numeral} ({result.name}) — score: {result.score:.2f}{confidence_tag}")

    if args.file:
        lines = [l.strip() for l in args.file.read_text().splitlines() if l.strip()]
        for line in lines:
            process(line)
            time.sleep(args.delay)
    else:
        print("Sonifying Embeddings — type text, hear its chord. Ctrl+C to quit.\n")
        try:
            while True:
                try:
                    text = input("> ").strip()
                except EOFError:
                    break
                if not text:
                    continue
                process(text)
        except KeyboardInterrupt:
            pass
        finally:
            print("\nGoodbye.")
            if bridge:
                bridge.close()


if __name__ == "__main__":
    main()
