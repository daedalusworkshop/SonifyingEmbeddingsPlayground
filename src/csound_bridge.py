"""
Manages the ctcsound lifecycle and plays chords in real time.
Spec: docs/specs/04-csound-bridge.md
"""

import atexit
from pathlib import Path

from chords import ChordResult

ROOT = Path(__file__).parent.parent
ORC_PATH = ROOT / "instruments" / "pad.orc"

DURATION = 2.0
AMPLITUDE = 0.4


class CsoundNotAvailableError(Exception):
    pass


class CsoundBridge:
    def __init__(self):
        try:
            import ctcsound
        except ImportError:
            raise CsoundNotAvailableError("ctcsound not installed")

        self._cs = ctcsound.Csound()
        self._cs.setOption("-odac")
        self._cs.setOption("-d")

        orc = ORC_PATH.read_text()
        ret = self._cs.compileOrc(orc)
        if ret != 0:
            raise CsoundNotAvailableError(f"Csound orchestra compile failed (code {ret})")

        self._cs.readScore("f0 3600")
        self._cs.start()

        self._pt = ctcsound.CsoundPerformanceThread(self._cs.csound())
        self._pt.play()

        atexit.register(self.close)

    def play_chord(self, result: ChordResult) -> None:
        confidence_tag = "  [LOW CONFIDENCE]" if result.low_confidence else ""
        print(f"Playing {result.numeral} ({result.name}) — score: {result.score:.2f}{confidence_tag}")

        # Stop any currently playing notes
        self._pt.inputMessage("i -1 0 0")

        for freq in result.frequencies:
            self._pt.scoreEvent(False, "i", [1, 0, DURATION, AMPLITUDE, freq])

    def play_progression(self, chords: list[ChordResult], tempo_bpm: float = 80) -> None:
        """Stub for future progression mode."""
        import time
        beat_duration = 60.0 / tempo_bpm
        for chord in chords:
            self.play_chord(chord)
            time.sleep(beat_duration * 2)

    def close(self) -> None:
        try:
            self._pt.stop()
            self._pt.join()
            self._cs.cleanup()
            self._cs.reset()
        except Exception:
            pass
