---
title: "feat: Chord Correction Loop"
type: feat
status: active
date: 2026-03-25
origin: docs/brainstorms/2026-03-25-chord-correction-loop-brainstorm.md
---

# feat: Chord Correction Loop

## Overview

Two deliverables:

1. **Correction UI** — right-click any resolved chord annotation in the editor → context menu with 7 chords → appends one line to `data/golden_cases.md`
2. **auto_improve.py** — CLI hill-climber that reads `golden_cases.md` as ground truth, finds failures, asks Claude to edit keyword pages, rebuilds, re-tests full set, keeps or reverts

---

## golden_cases.md format

Plain text, one case per line:

```
"the light fades slowly" → vi
"I'm finally home" → I
"something is very wrong here" → vii°
```

Human-readable and hand-editable. The model's opinion is not recorded — only what the user says the correct chord is. When the loop runs, it compares current model output against these. Green = agrees. Red = still wrong.

---

## Phase 1 — Correction UI in `editor.py`

**Add to `AnnotationPane`:**

```python
# new imports
from PyQt6.QtWidgets import QMenu, QAction
from src.chords import CHORDS

# in __init__
self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
self.customContextMenuRequested.connect(self._on_context_menu)

# new signal
correction_made = pyqtSignal(int, str)  # (annotation_row, chosen_numeral)
```

**`AnnotationPane._on_context_menu(pos)`:**
- `item = self.itemAt(pos)` — return if `None` or text is `"..."`
- Build `QMenu` with 7 `QAction` entries: `"numeral — name"`
- On trigger: emit `correction_made(row, numeral)`

**`ChordEditorWindow` wiring:**
- Connect `_annot.correction_made` → `_on_correction(row, numeral)`

**`ChordEditorWindow._on_correction(row, numeral)`:**
1. `line_index = _annotation_row.index(row)` — return if not found
2. `entry = _submitted[line_index]` — return if `entry["numeral"] is None` (still pending)
3. If `numeral == entry["numeral"]` → no-op
4. Get `ChordDef` from `CHORD_BY_NUMERAL[numeral]`
5. Build `ChordResult` (score=1.0, midi/freq from ChordDef)
6. `_annot.set_result(row, result)` — update annotation label
7. `_bridge.play_chord(result)` — play the corrected chord
8. Update `_submitted[line_index]`: numeral, name, score
9. Append to `data/golden_cases.md`:
   ```
   "{line}" → {numeral}
   ```

**Write helper:**
```python
def _save_golden_case(line: str, numeral: str) -> None:
    path = Path(__file__).parent.parent / "data" / "golden_cases.md"
    with open(path, "a") as f:
        f.write(f'"{line}" → {numeral}\n')
```

---

## Phase 2 — `src/auto_improve.py`

**Parse golden_cases.md:**
```python
import re
def load_cases(path) -> list[tuple[str, str]]:
    cases = []
    for line in path.read_text().splitlines():
        m = re.match(r'"(.+)" → (\S+)', line.strip())
        if m:
            cases.append((m.group(1), m.group(2)))
    return cases
```

**Benchmark (deterministic — argmax, not temperature sampling):**
```python
def run_benchmark(cases, clf) -> tuple[int, int]:
    passed = sum(1 for line, correct in cases
                 if clf.classify_deterministic(line) == correct)
    return passed, len(cases)
```

Add `classify_deterministic()` to `Classifier` (returns argmax numeral, no sampling) — stable across runs for reliable hill-climbing.

**Hill-climbing loop:**
```python
def run(max_iter=20):
    cases = load_cases(GOLDEN_PATH)
    if not cases:
        print("No golden cases yet. Build some in the editor first.")
        return

    pages = {c.keyword_file: read_page(c) for c in CHORDS}  # snapshot all 7 before loop
    clf = Classifier()
    baseline, total = run_benchmark(cases, clf)
    print(f"Baseline: {baseline}/{total}")

    for i in range(max_iter):
        failures = [(line, correct) for line, correct in cases
                    if clf.classify_deterministic(line) != correct]
        if not failures:
            print(f"All {total} pass. Done.")
            break

        proposal = ask_claude(failures, pages)
        # proposal: {"file": "vi-submediant.md", "new_content": "...full file..."}

        original = read_page(proposal["file"])
        write_page(proposal["file"], proposal["new_content"])
        anchor_builder.build(force=True)
        clf = Classifier()

        new_pass, _ = run_benchmark(cases, clf)
        delta = new_pass - baseline
        if new_pass >= baseline:
            print(f"  [{i+1}] {baseline} → {new_pass}/{total} ✓ kept")
            baseline = new_pass
            pages[proposal["file"]] = proposal["new_content"]
        else:
            print(f"  [{i+1}] {baseline} → {new_pass}/{total} ✗ reverted")
            write_page(proposal["file"], original)
            anchor_builder.build(force=True)
            clf = Classifier()
```

**Revert strategy:** In-memory copy of the file taken before the edit. If revert write fails, print a warning and exit — no silent corruption.

**Claude prompt:**
- All 7 current keyword pages
- The failing cases (line + expected chord)
- All 7 scores for each failing case from `classify_deterministic` (for signal)
- Instruction: "Edit ONE chord page to fix these failures without regressing passing cases. Return JSON: `{file, new_content}`."

---

## Files Changed

| File | Change |
|------|--------|
| `src/editor.py` | Add `QMenu`/`QAction` imports, `correction_made` signal, `_on_context_menu`, `_on_correction`, `_save_golden_case` |
| `src/classifier.py` | Add `classify_deterministic()` method (argmax, no sampling) |
| `src/auto_improve.py` | New file — hill-climbing loop |
| `docs/specs/07-auto-improve.md` | New spec (per CLAUDE.md convention) |
| `requirements.txt` | Add `anthropic` |

---

## Acceptance Criteria

- [ ] Right-click resolved annotation → 7-chord context menu appears
- [ ] Right-click pending `"..."` → nothing happens
- [ ] Selecting a chord plays it and updates the annotation label
- [ ] Selecting the same chord already shown → no-op
- [ ] `data/golden_cases.md` gets one line per correction in `"line" → numeral` format
- [ ] `auto_improve.py` exits cleanly if `golden_cases.md` missing or empty
- [ ] Loop uses `classify_deterministic()` (stable, reproducible results)
- [ ] Each iteration tests the full golden set (not just failures)
- [ ] Bad edits are reverted before next iteration
- [ ] `--max-iter N` flag (default 20)

---

## Sources

- **Origin brainstorm:** [docs/brainstorms/2026-03-25-chord-correction-loop-brainstorm.md](../brainstorms/2026-03-25-chord-correction-loop-brainstorm.md)
- `src/editor.py` — `AnnotationPane` lines 172–206; `_submitted` / `_annotation_row` lines 217–218
- `src/chords.py` — `CHORDS`, `CHORD_BY_NUMERAL`, `ChordResult` lines 26–51
- `src/classifier.py` — `Classifier.classify()` and temperature sampling
- `src/anchor_builder.py` — `build(force=True)` lines 51–90
