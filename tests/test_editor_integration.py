"""
Integration test for the chord editor GUI.

Exercises the real code path end-to-end:
  - actual Classifier (Qwen model + anchors)
  - real Qt key events through EditorPane.keyPressEvent
  - real ClassifierWorker QThread
  - dry-run mode (no audio required)

Run:
  python tests/test_editor_integration.py

Passes when every assertion prints OK and exits 0.
Fails with a traceback and exits 1.
"""

import os
import sys
import time
from pathlib import Path

# Offscreen platform — must be set before QApplication is created
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from chords import CHORDS
from editor import ChordEditorWindow


# ── Helpers ────────────────────────────────────────────────────────────────────

def pump(app: QApplication, seconds: float) -> None:
    """Process Qt events for `seconds` seconds."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)


def wait_for(app: QApplication, condition, timeout: float, label: str):
    """Pump events until condition() is True or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if condition():
            return
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for: {label}")


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_startup(app, window):
    """Window opens with editor disabled and status bar showing load message."""
    assert not window._editor._enabled, "Editor should be disabled before model loads"
    ok("editor disabled on startup")


def test_model_loads(app, window):
    """Classifier loads in background within 60s; editor becomes enabled."""
    wait_for(app, lambda: window._editor._enabled, timeout=60,
             label="model load + editor enable")
    ok("model loaded, editor enabled")


def test_blank_line_noop(app, window):
    """Pressing Return on a blank line does nothing."""
    before_count = window._annot.count()
    before_submitted = len(window._submitted)

    QTest.keyClick(window._editor, Qt.Key.Key_Return)
    pump(app, 0.3)

    assert window._annot.count() == before_count, "blank Return should not add annotation"
    assert len(window._submitted) == before_submitted, "blank Return should not append to submitted"
    ok("blank line is a no-op")


def test_line_submission(app, window):
    """Typing a line and pressing Return classifies it and shows annotation."""
    text = "I lost myself today"
    QTest.keyClicks(window._editor, text)
    pump(app, 0.1)
    QTest.keyClick(window._editor, Qt.Key.Key_Return)
    pump(app, 0.3)

    # Pending placeholder appears immediately
    assert window._annot.count() == 1, "annotation pane should have 1 item"
    assert window._annot.item(0).text() == "...", \
        f"pending item should show '...', got '{window._annot.item(0).text()}'"
    ok("pending '...' annotation appears immediately")

    # Wait for classification result (up to 30s on CPU)
    wait_for(app, lambda: window._annot.item(0) and window._annot.item(0).text() != "...",
             timeout=30, label="classification result replaces '...'")

    annotation = window._annot.item(0).text()
    valid_numerals = {c.numeral for c in CHORDS}
    numeral = annotation.split(" ")[0]
    assert numeral in valid_numerals, f"annotation '{annotation}' has invalid numeral"
    assert len(window._submitted) == 1
    assert window._submitted[0]["line"] == text
    assert window._submitted[0]["numeral"] is not None

    ok(f"annotation resolved: '{annotation}'")


def test_cursor_advances(app, window):
    """After submission the cursor is on a new blank last line."""
    doc = window._editor.document()
    cursor = window._editor.textCursor()
    assert cursor.blockNumber() == doc.blockCount() - 1, \
        "cursor should be on the last (blank) block after submission"
    ok("cursor advanced to new blank line")


def test_second_line(app, window):
    """A second line submission adds a second annotation."""
    text = "The light came back and everything felt possible"
    QTest.keyClicks(window._editor, text)
    QTest.keyClick(window._editor, Qt.Key.Key_Return)
    pump(app, 0.3)

    assert window._annot.count() == 2, f"expected 2 annotations, got {window._annot.count()}"
    ok("second annotation placeholder added")

    wait_for(app, lambda: window._annot.item(1) and window._annot.item(1).text() != "...",
             timeout=30, label="second classification result")

    annotation = window._annot.item(1).text()
    numeral = annotation.split(" ")[0]
    assert numeral in {c.numeral for c in CHORDS}
    ok(f"second annotation resolved: '{annotation}'")


def test_export(app, window, tmp_path):
    """Export writes valid .json and .txt files."""
    import json as _json
    base = tmp_path / "session"
    json_path = base.with_suffix(".json")
    txt_path  = base.with_suffix(".txt")

    # Drive _export directly (avoids needing a real file dialog)
    submitted_snapshot = list(window._submitted)
    window._export_to(str(base))

    assert json_path.exists(), ".json file not written"
    assert txt_path.exists(),  ".txt file not written"

    data = _json.loads(json_path.read_text())
    assert isinstance(data, list)
    assert len(data) == len(submitted_snapshot)
    for entry in data:
        assert "line" in entry and "numeral" in entry and "score" in entry

    lines = txt_path.read_text().splitlines()
    assert len(lines) == len(submitted_snapshot)
    for line in lines:
        assert "  |  " in line

    ok(f"export wrote {json_path.name} ({len(data)} entries) and {txt_path.name}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    import tempfile

    app = QApplication.instance() or QApplication(sys.argv)
    window = ChordEditorWindow(dry_run=True)
    window.show()

    tmp = Path(tempfile.mkdtemp())
    failures = []

    tests = [
        ("startup",         lambda: test_startup(app, window)),
        ("model loads",     lambda: test_model_loads(app, window)),
        ("blank line noop", lambda: test_blank_line_noop(app, window)),
        ("line submission", lambda: test_line_submission(app, window)),
        ("cursor advances", lambda: test_cursor_advances(app, window)),
        ("second line",     lambda: test_second_line(app, window)),
        ("export",          lambda: test_export(app, window, tmp)),
    ]

    print(f"\nChord Editor — integration tests\n{'─'*40}")
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
        except Exception as exc:
            print(f"  FAIL {exc}")
            failures.append((name, exc))

    window.close()
    pump(app, 1.0)

    print(f"\n{'─'*40}")
    if failures:
        print(f"FAILED  {len(failures)}/{len(tests)} tests")
        for name, exc in failures:
            print(f"  • {name}: {exc}")
        sys.exit(1)
    else:
        print(f"PASSED  {len(tests)}/{len(tests)} tests")
        sys.exit(0)


if __name__ == "__main__":
    main()
