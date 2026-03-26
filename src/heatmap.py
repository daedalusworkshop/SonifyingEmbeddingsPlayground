"""
2D scatter plot of chord anchor embeddings via PCA.
Proximity = similarity in embedding space = more likely to be confused.
Run: python src/heatmap.py
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from sklearn.decomposition import PCA
from sentence_transformers import util

sys.path.insert(0, str(Path(__file__).parent))
import anchor_builder
from chords import CHORDS

# ── data ──────────────────────────────────────────────────────────────────────
anchors = anchor_builder.build()
vectors = anchors.float().cpu().numpy()          # (7, 1024)
coords  = PCA(n_components=2).fit_transform(vectors)  # (7, 2)

labels = [c.numeral for c in CHORDS]
emotions = {
    "I":    "Home /\nResolution",
    "ii":   "Private\nSadness",
    "iii":  "Liminal /\nUnnamed",
    "IV":   "Aspiration /\nDevotion",
    "V":    "Tension /\nUrgency",
    "vi":   "Grief /\nHeartbreak",
    "vii°": "Dread /\nDanger",
}
colors = {
    "I":    "#4CAF50",
    "ii":   "#90A4AE",
    "iii":  "#B39DDB",
    "IV":   "#FFD54F",
    "V":    "#FF8A65",
    "vi":   "#EF9A9A",
    "vii°": "#EF5350",
}

# ── draw lines between close pairs ────────────────────────────────────────────
sim = util.cos_sim(anchors, anchors).float().cpu().numpy()

fig, ax = plt.subplots(figsize=(9, 7))
fig.patch.set_facecolor("#1a1a2e")
ax.set_facecolor("#1a1a2e")

for i in range(len(CHORDS)):
    for j in range(i + 1, len(CHORDS)):
        s = sim[i][j]
        if s > 0.62:                              # only draw meaningful proximity
            alpha = (s - 0.62) / (1.0 - 0.62)   # scale 0→1 over that range
            ax.plot(
                [coords[i, 0], coords[j, 0]],
                [coords[i, 1], coords[j, 1]],
                color="white", alpha=alpha * 0.35, linewidth=alpha * 2.5, zorder=1,
            )

# ── dots ──────────────────────────────────────────────────────────────────────
for i, chord in enumerate(CHORDS):
    x, y = coords[i]
    c = colors[chord.numeral]
    ax.scatter(x, y, s=320, color=c, zorder=3, edgecolors="white", linewidths=1.2)
    ax.text(x, y, chord.numeral, ha="center", va="center",
            fontsize=9, fontweight="bold", color="black", zorder=4)

# ── emotion labels — push outward from centroid ───────────────────────────────
cx, cy = coords[:, 0].mean(), coords[:, 1].mean()
pad = (coords[:, 0].ptp() + coords[:, 1].ptp()) * 0.13   # ~13% of spread

for i, chord in enumerate(CHORDS):
    x, y = coords[i]
    dx, dy = x - cx, y - cy
    norm = max(np.hypot(dx, dy), 1e-9)
    ox, oy = dx / norm * pad, dy / norm * pad
    ax.text(x + ox, y + oy, emotions[chord.numeral],
            ha="center", va="center", fontsize=7.5, color="#cccccc",
            linespacing=1.4,
            path_effects=[pe.withStroke(linewidth=2, foreground="#1a1a2e")])

# ── labels & legend ───────────────────────────────────────────────────────────
ax.set_title("Chord Emotional Landscape", fontsize=14, color="white", pad=16, fontweight="bold")
ax.set_xlabel("axes have no meaning — only distance between dots matters",
              fontsize=8, color="#555555", style="italic")
ax.set_yticks([])
ax.set_xticks([])
# zoom tight with padding
margin = (coords[:, 0].ptp() + coords[:, 1].ptp()) * 0.22
ax.set_xlim(coords[:, 0].min() - margin, coords[:, 0].max() + margin)
ax.set_ylim(coords[:, 1].min() - margin, coords[:, 1].max() + margin)
for spine in ax.spines.values():
    spine.set_edgecolor("#333333")

note = (
    "Each dot is a chord's emotional 'fingerprint' in embedding space.\n"
    "Dots close together = the model may confuse those chords.\n"
    "Lines show high similarity — thicker = more likely to bleed."
)
fig.text(0.5, 0.01, note, ha="center", fontsize=7.5, color="#888888",
         style="italic", wrap=True)

plt.tight_layout(rect=[0, 0.06, 1, 1])
plt.show()
