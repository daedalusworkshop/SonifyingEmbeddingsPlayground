"""
Manages the ctcsound lifecycle and plays chords in real time.
Spec: docs/specs/04-csound-bridge.md
"""

import atexit
from pathlib import Path

from chords import ChordResult

ROOT = Path(__file__).parent.parent
ORC_PATH = ROOT / "instruments" / "pad.orc"

DURATION = 3600.0  # hold until explicitly stopped by the next chord
AMPLITUDE = 0.15
DRONE_FREQ = 130.81   # C3 — root of I
DRONE_AMP  = 0.12


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

        # Start tonic drone on instr 2 (runs for session lifetime, survives chord changes)
        self._pt.scoreEvent(False, "i", [2, 0, 3600, DRONE_AMP, DRONE_FREQ])

        atexit.register(self.close)

    def play_chord(self, result: ChordResult) -> None:
        confidence_tag = "  [LOW CONFIDENCE]" if result.low_confidence else ""
        print(f"Playing {result.numeral} ({result.name}) — score: {result.score:.2f}{confidence_tag}")

        # instr 99 runs turnoff2 × 3 inside Csound — reliably stops all 3 voices.
        # External inputMessage cannot find notes started via scoreEvent (produces
        # "could not find playing instr 1.000000" — verified in production logs).
        self._pt.scoreEvent(False, "i", [99, 0, 0.001])

        # New voices start 50 ms later; old voices release for 50 ms (natural fade)
        for freq in result.frequencies:
            self._pt.scoreEvent(False, "i", [1, 0.05, DURATION, AMPLITUDE, freq])

    def stop_all(self) -> None:
        """Stop all playing chord voices (leaves drone intact)."""
        self._pt.scoreEvent(False, "i", [99, 0, 0.001])

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
