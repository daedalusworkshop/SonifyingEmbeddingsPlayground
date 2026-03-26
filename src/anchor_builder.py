"""
Builds and caches anchor embeddings from chord keyword pages.
Spec: docs/specs/02-anchor-embeddings.md
"""

import hashlib
import json
import re
from pathlib import Path

import torch
from sentence_transformers import SentenceTransformer, util

from chords import CHORDS

ROOT = Path(__file__).parent.parent
CHORDS_DIR = ROOT / "data" / "chords"
ANCHORS_PATH = ROOT / "data" / "anchors.pt"
META_PATH = ROOT / "data" / "anchors_meta.json"
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
INSTRUCTION = (
    "Instruct: Represent this text by its emotional and affective character "
    "for matching to a musical chord.\nQuery: "
)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_stale() -> bool:
    if not ANCHORS_PATH.exists() or not META_PATH.exists():
        return True
    meta = json.loads(META_PATH.read_text())
    if meta.get("model") != MODEL_NAME:
        return True
    for chord in CHORDS:
        fp = CHORDS_DIR / chord.keyword_file
        if meta["hashes"].get(chord.keyword_file) != _hash_file(fp):
            return True
    return False


def _strip_markdown(text: str) -> str:
    # Remove markdown headers and bullet characters, keep the words
    text = re.sub(r"^#+\s.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s", "", text, flags=re.MULTILINE)
    return text.strip()


def build(force: bool = False) -> torch.Tensor:
    if not force and not _is_stale():
        return torch.load(ANCHORS_PATH, weights_only=True)

    print("Building anchor embeddings...")
    model = SentenceTransformer(MODEL_NAME)

    texts = []
    hashes = {}
    for chord in CHORDS:
        fp = CHORDS_DIR / chord.keyword_file
        raw = fp.read_text()
        texts.append(INSTRUCTION + _strip_markdown(raw))
        hashes[chord.keyword_file] = _hash_file(fp)

    anchors = model.encode(texts, convert_to_tensor=True, normalize_embeddings=True)

    # Validate separation
    sim_matrix = util.cos_sim(anchors, anchors)
    labels = [c.numeral for c in CHORDS]
    print("\nAnchor pairwise cosine similarities:")
    header = "       " + "  ".join(f"{l:>5}" for l in labels)
    print(header)
    for i, row_label in enumerate(labels):
        row = "  ".join(f"{sim_matrix[i][j].item():.3f}" for j in range(len(labels)))
        print(f"  {row_label:>5}  {row}")

    # Warn on poor separation
    for i in range(len(CHORDS)):
        for j in range(i + 1, len(CHORDS)):
            val = sim_matrix[i][j].item()
            if val > 0.85:
                print(f"\n⚠️  WARNING: {labels[i]} and {labels[j]} have similarity {val:.3f} > 0.85")
                print("   Consider revising these keyword pages to increase distinctiveness.\n")

    ANCHORS_PATH.parent.mkdir(exist_ok=True)
    torch.save(anchors, ANCHORS_PATH)
    META_PATH.write_text(json.dumps({"model": MODEL_NAME, "hashes": hashes}, indent=2))
    print(f"\nAnchors saved to {ANCHORS_PATH}\n")
    return anchors


if __name__ == "__main__":
    build(force=True)
