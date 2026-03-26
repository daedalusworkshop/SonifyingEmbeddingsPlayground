---
title: "MPS device mismatch crashes classifier inside QThread"
date: 2026-03-25
module: editor
problem_type: runtime_error
component: chord_classifier
severity: high
symptoms:
  - "RuntimeError: Expected all tensors to be on the same device"
  - "Crash only occurs inside QThread, not in the main REPL loop"
  - "Works fine on CPU-only machines and in main.py"
root_cause: thread_violation
tags:
  - mps
  - qthread
  - torch
  - pyqt6
  - apple-silicon
---

## Problem

The classifier ran correctly in `main.py` but raised a device mismatch error when
invoked from `ClassifierWorker` (a `QThread`) inside `editor.py`. On Apple Silicon,
PyTorch's MPS backend acquires a device context on the main thread; that context is
not accessible from worker threads. The crash manifested during attention computation
inside the Qwen embedding model.

Additionally, `anchors.pt` is cached to the MPS device at load time (since the main
thread has MPS available), so even after forcing the model to CPU inside the thread,
the anchor tensor was still on MPS — causing a secondary mismatch at similarity scoring.

## Root Cause

Two compounding issues:
1. PyTorch MPS does not support cross-thread tensor operations.
2. `anchor_builder.build()` returns tensors on whatever device the model was loaded
   on at cache time — if MPS was used when `anchors.pt` was written, loading it
   restores the MPS device, not CPU.

## Solution

In `ClassifierWorker.run()` (before instantiating `Classifier`):
1. Monkey-patch `torch.backends.mps.is_available` to return `False` so
   `SentenceTransformer` picks CPU.
2. After `Classifier()` loads, explicitly move anchors to CPU:
   `self._classifier.anchors = self._classifier.anchors.cpu()`

```python
def run(self) -> None:
    try:
        import torch
        torch.backends.mps.is_available = lambda: False  # type: ignore[method-assign]
    except Exception:
        pass

    try:
        self._classifier = Classifier()
        self._classifier.anchors = self._classifier.anchors.cpu()
    except Exception as exc:
        self.error.emit(str(exc))
        return
```

## Prevention

- Never share a `Classifier` instance (or any model) across thread boundaries on MPS.
- Always instantiate models fresh inside the thread that will use them.
- After loading anchors in a thread context, always call `.cpu()` to guarantee device
  consistency regardless of what device was used when `anchors.pt` was written.
- When adding new background threads that call the classifier, reproduce this pattern.
