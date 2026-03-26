"""
Chord Editor — minimalist PyQt6 text editor that classifies each line on Return.
Spec: docs/specs/06-editor.md

Usage:
  python src/editor.py
  python src/editor.py --dry-run
"""

import argparse
import json
import queue
import sys
from pathlib import Path

# Allow running from project root or from src/
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QWidget,
)

from chords import ChordResult
from classifier import Classifier
from csound_bridge import CsoundBridge, CsoundNotAvailableError


# ── Colours ────────────────────────────────────────────────────────────────────

BG         = "#1a1a1a"
FG         = "#e0e0e0"
ANNOT_FG   = "#888888"
PENDING_FG = "#555555"
BORDER     = "#2a2a2a"


# ── Background worker ──────────────────────────────────────────────────────────

class ClassifierWorker(QThread):
    """Single background thread: loads the model, then processes classify requests."""

    ready  = pyqtSignal()                          # emitted once when Classifier is loaded
    error  = pyqtSignal(str)                       # emitted if load fails
    result = pyqtSignal(int, object)               # (line_index, ChordResult)

    def __init__(self):
        super().__init__()
        self._queue: queue.Queue = queue.Queue()
        self._stop = False
        self._classifier: Classifier | None = None

    def enqueue(self, line_index: int, text: str) -> None:
        self._queue.put((line_index, text))

    def stop_worker(self) -> None:
        self._stop = True
        self._queue.put(None)  # unblock get()

    def run(self) -> None:
        try:
            self._classifier = Classifier()
        except Exception as exc:
            self.error.emit(str(exc))
            return

        self.ready.emit()

        while not self._stop:
            item = self._queue.get()
            if item is None:
                break
            line_index, text = item
            result = self._classifier.classify(text)
            self.result.emit(line_index, result)


# ── Editor text widget ─────────────────────────────────────────────────────────

class EditorPane(QPlainTextEdit):
    """Left pane: only the last (bottom) line is editable."""

    line_submitted = pyqtSignal(int, str)   # (line_index, text)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False  # True once the model is loaded

    def enable_editing(self) -> None:
        self._enabled = True
        self.setReadOnly(False)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._enabled:
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text().strip()

            if not text:
                # Blank line — no-op
                event.accept()
                return

            # How many lines have already been submitted (all blocks except the last)
            doc = self.document()
            line_index = doc.blockCount() - 1  # 0-based index of the current (last) block

            self.line_submitted.emit(line_index, text)

            # Append a new blank line and move cursor there
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText("\n")
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            event.accept()
            return

        # Block navigation into completed lines (only the last block is editable)
        cursor = self.textCursor()
        doc = self.document()
        last_block = doc.lastBlock()

        # Intercept keys that would move the cursor off the last block
        nav_keys = {
            Qt.Key.Key_Up, Qt.Key.Key_Left, Qt.Key.Key_Home,
            Qt.Key.Key_PageUp,
        }
        if event.key() in nav_keys:
            # Allow cursor movement but prevent editing — handled by the block guard below
            super().keyPressEvent(event)
            # If cursor has moved off the last block, snap it back
            if self.textCursor().blockNumber() != last_block.blockNumber():
                c = self.textCursor()
                c.movePosition(c.MoveOperation.End)
                self.setTextCursor(c)
            return

        # If cursor is not on the last block, snap it back before applying input
        if cursor.blockNumber() != last_block.blockNumber():
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)

        super().keyPressEvent(event)


# ── Annotation column ──────────────────────────────────────────────────────────

class AnnotationPane(QListWidget):
    """Right pane: one item per submitted line."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"""
            QListWidget {{
                background: {BG};
                border: none;
                border-left: 1px solid {BORDER};
                padding: 0;
            }}
            QListWidget::item {{
                color: {ANNOT_FG};
                padding: 0 8px;
            }}
        """)

    def add_pending(self) -> int:
        """Append a '...' placeholder; return the new item's row."""
        item = QListWidgetItem("...")
        item.setForeground(QColor(PENDING_FG))
        self.addItem(item)
        return self.count() - 1

    def set_result(self, row: int, result: ChordResult) -> None:
        label = f"{result.numeral} — {result.name}  {result.score:.2f}"
        item = self.item(row)
        if item:
            item.setText(label)
            item.setForeground(QColor(ANNOT_FG))


# ── Main window ────────────────────────────────────────────────────────────────

class ChordEditorWindow(QMainWindow):

    def __init__(self, dry_run: bool = False):
        super().__init__()
        self._dry_run = dry_run
        self._bridge: CsoundBridge | None = None
        self._submitted: list[dict] = []  # [{line, numeral, name, score, low_confidence}]
        self._annotation_row: list[int] = []  # maps line_index → annotation pane row

        self.setWindowTitle("Chord Editor")
        self.setMinimumSize(900, 500)
        self._setup_ui()
        self._setup_worker()
        if not dry_run:
            self._init_csound()

    # ── UI setup ───────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)

        # Left pane
        self._editor = EditorPane()
        self._editor.setReadOnly(True)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._editor.line_submitted.connect(self._on_line_submitted)

        # Right pane
        self._annot = AnnotationPane()
        self._annot.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._annot.setFixedWidth(220)

        splitter.addWidget(self._editor)
        splitter.addWidget(self._annot)
        splitter.setSizes([680, 220])

        layout.addWidget(splitter)

        # Style
        font = self._monospace_font(13)
        self._editor.setFont(font)
        self._annot.setFont(self._monospace_font(12))

        self._editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {BG};
                color: {FG};
                border: none;
                padding: 8px;
                selection-background-color: #2a4a6a;
            }}
        """)

        central.setStyleSheet(f"background: {BG};")

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet(f"""
            QStatusBar {{
                background: {BG};
                color: {ANNOT_FG};
                border-top: 1px solid {BORDER};
            }}
        """)
        self.setStatusBar(self._status)
        self._status.showMessage("Loading model…")

        self.setStyleSheet(f"background: {BG};")

    @staticmethod
    def _monospace_font(size: int) -> QFont:
        for family in ("Menlo", "Courier New", "monospace"):
            font = QFont(family, size)
            if QFontDatabase.hasFamily(family):
                font.setFixedPitch(True)
                return font
        font = QFont()
        font.setFixedPitch(True)
        font.setPointSize(size)
        return font

    # ── Worker setup ───────────────────────────────────────────────────────────

    def _setup_worker(self) -> None:
        self._worker = ClassifierWorker()
        self._worker.ready.connect(self._on_model_ready)
        self._worker.error.connect(self._on_model_error)
        self._worker.result.connect(self._on_classify_result)
        self._worker.start()

    def _on_model_ready(self) -> None:
        self._status.clearMessage()
        self._editor.enable_editing()
        self._editor.setFocus()

    def _on_model_error(self, msg: str) -> None:
        self._status.showMessage(f"Model load failed: {msg}")

    # ── Csound setup ───────────────────────────────────────────────────────────

    def _init_csound(self) -> None:
        try:
            self._bridge = CsoundBridge()
        except CsoundNotAvailableError:
            self._bridge = None  # dry-run fallback, silent

    # ── Line submission flow ───────────────────────────────────────────────────

    def _on_line_submitted(self, line_index: int, text: str) -> None:
        # Add pending annotation
        row = self._annot.add_pending()
        self._annotation_row.append(row)

        # Track the line for export (pending state)
        self._submitted.append({
            "line": text,
            "numeral": None,
            "name": None,
            "score": None,
            "low_confidence": None,
        })

        # Enqueue classification
        self._worker.enqueue(line_index, text)

        # Sync annotation pane scroll with editor
        self._sync_scroll()

    def _on_classify_result(self, line_index: int, result: ChordResult) -> None:
        # line_index == submitted list index: block N was the (N+1)th line submitted
        submitted_index = line_index

        # Update annotation pane
        if submitted_index < len(self._annotation_row):
            row = self._annotation_row[submitted_index]
            self._annot.set_result(row, result)

        # Update export record
        if submitted_index < len(self._submitted):
            self._submitted[submitted_index].update({
                "numeral": result.numeral,
                "name": result.name,
                "score": round(result.score, 4),
                "low_confidence": result.low_confidence,
            })

        # Play or dry-run print
        if self._bridge:
            self._bridge.play_chord(result)
        else:
            confidence_tag = "  [LOW CONFIDENCE]" if result.low_confidence else ""
            print(f"[dry-run] {result.numeral} ({result.name}) — score: {result.score:.2f}{confidence_tag}")

    # ── Scroll sync ────────────────────────────────────────────────────────────

    def _sync_scroll(self) -> None:
        """Keep annotation pane scrolled to match the editor's last line."""
        self._annot.scrollToBottom()

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export chord session",
            "",
            "All files (*)",
        )
        if not path:
            return

        base = Path(path)
        # Strip any extension the user typed so we always write .json and .txt
        if base.suffix in (".json", ".txt"):
            base = base.with_suffix("")

        json_path = base.with_suffix(".json")
        txt_path  = base.with_suffix(".txt")

        json_path.write_text(json.dumps(self._submitted, indent=2, ensure_ascii=False))

        lines = []
        for entry in self._submitted:
            if entry["numeral"] is not None:
                annot = f"{entry['numeral']} — {entry['name']}  {entry['score']:.2f}"
            else:
                annot = "..."
            lines.append(f"{entry['line']}  |  {annot}")
        txt_path.write_text("\n".join(lines) + "\n")

        self._status.showMessage(f"Saved {json_path.name} + {txt_path.name}", 4000)

    # ── Keyboard shortcuts ─────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        save_shortcut = (
            event.key() == Qt.Key.Key_S
            and event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier)
        )
        if save_shortcut:
            self._export()
            event.accept()
            return
        super().keyPressEvent(event)

    # ── Shutdown ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._worker.stop_worker()
        self._worker.wait(2000)
        if self._bridge:
            self._bridge.close()
        event.accept()


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Chord Editor — type text, hear chords")
    p.add_argument("--dry-run", action="store_true", help="Print results without audio")
    return p.parse_args()


def main():
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Chord Editor")
    window = ChordEditorWindow(dry_run=args.dry_run)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
