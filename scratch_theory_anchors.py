"""
Scratch: does embedding pure music theory descriptions work as anchors?

Run from repo root:
    python scratch_theory_anchors.py

No files modified. Nothing cached. Just a vibe check.
"""

import re
import torch
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
CHORDS_DIR = Path("data/chords")

# Pure technical descriptions — no emotional language
THEORY_ANCHORS = [
    ("I",    "C major",       "I chord: C major triad, notes C E G, tonic function, first scale degree, C major"),
    ("ii",   "D minor",       "ii chord: D minor triad, notes D F A, supertonic function, second scale degree, C major"),
    ("iii",  "E minor",       "iii chord: E minor triad, notes E G B, mediant function, third scale degree, C major"),
    ("IV",   "F major",       "IV chord: F major triad, notes F A C, subdominant function, fourth scale degree, C major"),
    ("V",    "G major",       "V chord: G major triad, notes G B D, dominant function, fifth scale degree, C major"),
    ("vi",   "A minor",       "vi chord: A minor triad, notes A C E, submediant function, sixth scale degree, C major"),
    ("vii°", "B diminished",  "vii° chord: B diminished triad, notes B D F, leading tone function, seventh scale degree, C major"),
]

MD_FILES = [
    ("I",    "C major",      "I-tonic.md"),
    ("ii",   "D minor",      "ii-supertonic.md"),
    ("iii",  "E minor",      "iii-mediant.md"),
    ("IV",   "F major",      "IV-subdominant.md"),
    ("V",    "G major",      "V-dominant.md"),
    ("vi",   "A minor",      "vi-submediant.md"),
    ("vii°", "B diminished", "viidim-leading.md"),
]

# The instruction currently used for queries
QUERY_INSTRUCTION = (
    "Instruct: Represent this text by its emotional and affective character "
    "for matching to a musical chord.\nQuery: "
)
ANCHOR_INSTRUCTION = (
    "Instruct: Represent this text by its emotional and affective character "
    "for matching to a musical chord.\nQuery: "
)


def load_md(filename: str, adjectives_only: bool = False) -> str:
    text = (CHORDS_DIR / filename).read_text()
    if adjectives_only:
        # Keep only content up to (but not including) ## Extended Phrases
        text = re.split(r"##\s+Extended Phrases", text)[0]
    # Strip markdown headers and bullet points
    text = re.sub(r"^#+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    return text.strip()

# Test inputs: (label, expected chord numeral)
# ~5 cases per chord, varied phrasing and register
TEST_INPUTS = [
    # I — tonic: settled, complete, resolved, at rest
    ("I feel settled and at home",                          "I"),
    ("everything is resolved and still",                    "I"),
    ("solid ground, nothing more to prove",                 "I"),
    ("the journey is over, I have arrived",                 "I"),
    ("complete, whole, nothing missing",                    "I"),

    # ii — supertonic: yearning, gentle questioning, reaching
    ("curious, wandering, not quite there",                 "ii"),
    ("reaching for something just out of grasp",            "ii"),
    ("a gentle question with no answer yet",                "ii"),
    ("longing that hasn't turned to sadness",               "ii"),
    ("hopeful unease, moving toward something uncertain",   "ii"),

    # iii — mediant: introspective, ambiguous, inward
    ("lost in thought, somewhere between",                  "iii"),
    ("neither here nor there, suspended",                   "iii"),
    ("a quiet reverie, turned inward",                      "iii"),
    ("soft and internal, half-dreaming",                    "iii"),

    # IV — subdominant: open, expansive, generous, leaving home
    ("soft and dreamy, not quite home",                     "IV"),
    ("wide open sky, room to breathe",                      "IV"),
    ("stepping outside into morning light",                 "IV"),
    ("expansive, generous, unhurried",                      "IV"),
    ("looking out over a vast and open landscape",          "IV"),

    # V — dominant: tension, urgency, anticipation, coiled energy
    ("something is coming, building up",                    "V"),
    ("tension, anticipation, about to break",               "V"),
    ("held breath before the plunge",                       "V"),
    ("coiled energy, ready to release",                     "V"),
    ("the moment before the answer arrives",                "V"),

    # vi — submediant: bittersweet, nostalgic, aching sadness
    ("wistful, bittersweet, nostalgic",                     "vi"),
    ("gentle sadness, looking back",                        "vi"),
    ("missing someone who is gone",                         "vi"),
    ("autumn light through a window, beautiful and sad",    "vi"),
    ("the ache of something precious that has passed",      "vi"),

    # vii° — leading tone: dissonant, unstable, anxious, broken
    ("dark, unstable, dissonant",                           "vii°"),
    ("wrong notes, something is broken",                    "vii°"),
    ("vertigo, the ground is shifting beneath me",          "vii°"),
    ("sharp discomfort, nothing fits",                      "vii°"),
    ("the moment before everything falls apart",            "vii°"),
]


def run(label: str, chord_tuples: list, model: SentenceTransformer):
    print(f"\n{'='*60}")
    print(label)
    print('='*60)

    anchor_texts = [ANCHOR_INSTRUCTION + text for _, _, text in chord_tuples]
    anchors = model.encode(anchor_texts, convert_to_tensor=True, normalize_embeddings=True)

    correct = 0
    per_chord: dict[str, list[bool]] = {}
    for text, expected in TEST_INPUTS:
        query = QUERY_INSTRUCTION + text
        emb = model.encode(query, convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(emb, anchors)[0]
        best_idx = int(sims.argmax())
        numeral, name, _ = chord_tuples[best_idx]
        hit = numeral == expected
        per_chord.setdefault(expected, []).append(hit)
        marker = "✓" if hit else f"✗ (→ {numeral})"
        score = float(sims[best_idx])
        print(f"  [{marker}] '{text}'  ({score:.3f})")
        if hit:
            correct += 1

    print(f"\n  {correct}/{len(TEST_INPUTS)} correct")
    print("  per chord:", {k: f"{sum(v)}/{len(v)}" for k, v in sorted(per_chord.items())})
    print()


# Grounded keywords: dense, direct, concrete — drawn from music psychology
# research on chord affect (valence, arousal, tension ratings, listener studies).
# No poetic abstraction — just what listeners actually report feeling.
GROUNDED_ANCHORS = [
    ("I", "C major", (
        "stable consonant resolved complete satisfied certain confident calm peaceful "
        "pure bright major happy secure grounded strong definitive final closed whole "
        "centered clear undisturbed balanced pleasant comfortable restful steady solid "
        "anchored conclusive finished arrived done recognized confirmed established"
    )),
    ("ii", "D minor", (
        "yearning longing reaching seeking desiring wanting unfulfilled incomplete "
        "gentle sad tender soft melancholic questioning searching hopeful uncertain "
        "mild tension wistful minor subdued hushed pining aching sweet sorrow "
        "aspirational forward-leaning not-yet almost pre-dominant preparatory "
        "delicate restrained subdued bittersweet wistful pensive quiet sadness"
    )),
    ("iii", "E minor", (
        "ambiguous uncertain introspective contemplative suspended dreamy pensive "
        "hesitant quiet inward thoughtful reflective meditative obscure vague "
        "neither major nor minor feeling neutral soft withdrawn floating detached "
        "private subtle understated shadowy elusive mysterious indirect muted "
        "liminal between transitional unclear uncommitted passive introverted"
    )),
    ("IV", "F major", (
        "open expansive spacious warm bright generous broad optimistic gentle major "
        "relaxed unhurried free departing away from home uplifting airy light "
        "breathing room wide horizon fresh pastoral serene sunny mild benevolent "
        "soft strength dignified noble hymn-like devotional reverent calm uplift "
        "hopeful forward moving subdominant preparation pre-cadential departure"
    )),
    ("V", "G major", (
        "tense urgent active propulsive energetic exciting anticipatory dynamic "
        "leading pressing forward building unstable unresolved driving forceful "
        "strong bright major dominant expectation imminent arrival coming soon "
        "coiled ready preparing momentum charged building pressure suspense "
        "striving pushing demanding insistent restless forward drive"
    )),
    ("vi", "A minor", (
        "sad melancholic sorrowful grieving mourning wistful nostalgic longing "
        "beautiful sadness aching tender emotional dark somber minor bittersweet "
        "reflective introspective regret loss missing absence yearning gentle pain "
        "autumnal elegiac poignant touching moving heartfelt sincere vulnerable "
        "romantic sentimental wistful memory past love loss submediant relative minor"
    )),
    ("vii°", "B diminished", (
        "dissonant unstable tense harsh sharp anxious restless dark diminished "
        "tritone leading tone unresolved disturbing uncomfortable unsettling "
        "chromatic urgent desperate frantic edgy nervous frightening threatening "
        "chaotic broken wrong harsh clashing conflict disturbed agitated frantic "
        "high tension maximum instability crisis alarm danger collapse falling apart"
    )),
]


def run_affect_space(label: str, mapper_class, **mapper_kwargs):
    """Run the 34-case test using the affect space approach (no embedding model)."""
    import sys
    sys.path.insert(0, "src")
    from affect_space import nearest_chord, all_distances
    from chords import CHORDS

    numerals = [c.numeral for c in CHORDS]
    mapper = mapper_class(**mapper_kwargs)

    print(f"\n{'='*60}")
    print(label)
    print('='*60)

    correct = 0
    per_chord: dict[str, list[bool]] = {}
    for text, expected in TEST_INPUTS:
        query_vec = mapper.map(text)
        winner, dist = nearest_chord(query_vec, numerals)
        hit = winner == expected
        per_chord.setdefault(expected, []).append(hit)
        marker = "✓" if hit else f"✗ (→ {winner})"
        print(f"  [{marker}] '{text}'  (dist={dist:.3f})")
        if hit:
            correct += 1

    print(f"\n  {correct}/{len(TEST_INPUTS)} correct")
    print("  per chord:", {k: f"{sum(v)}/{len(v)}" for k, v in sorted(per_chord.items())})
    print()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")
    from query_mapper import LexiconMapper, PromptedMapper

    # ---- Embedding-based variants (use Qwen) ----
    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    # Variant 1: pure theory labels
    run("THEORY LABELS (pure music theory, no emotional language)", THEORY_ANCHORS, model)

    # Variant 2: full .md pages (current system baseline)
    full_md = [(n, name, load_md(f)) for n, name, f in MD_FILES]
    run("FULL .MD PAGES (current system baseline)", full_md, model)

    # Variant 3: .md pages — adjectives only, no Extended Phrases
    adj_only = [(n, name, load_md(f, adjectives_only=True)) for n, name, f in MD_FILES]
    run(".MD ADJECTIVES ONLY (Extended Phrases stripped)", adj_only, model)

    # Variant 4: dense grounded keywords, no poetic abstraction
    run("GROUNDED KEYWORDS (dense, direct, research-grounded)", GROUNDED_ANCHORS, model)

    # ---- Affect space variants (no embedding model) ----
    run_affect_space("AFFECT SPACE + LEXICON MAPPER (VADER)", LexiconMapper)

    try:
        run_affect_space("AFFECT SPACE + PROMPTED MAPPER (Claude)", PromptedMapper)
    except Exception as e:
        print(f"\n[Prompted mapper skipped: {e}]\n")
