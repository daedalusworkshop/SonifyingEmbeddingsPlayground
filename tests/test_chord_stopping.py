"""
Tests that prove chord voices do not accumulate across successive play_chord calls.

Root cause of the bug (observed in production logs):
    scoreEvent(False, "i", [1.001, 0.01, ...])  ← starts a note in Csound
    inputMessage("i -1.001 0 0")                 ← FAILS to stop it
    Csound output: "could not find playing instr 1.000000"

The fix: use instr 99 inside the orchestra to run `turnoff2` (or a global
kill-flag) against instr 1. Instr-internal operations are guaranteed to find
and stop active voices; external inputMessage with fractional IDs is not.

The simulation here models Csound's actual observed behavior:
  - inputMessage stops: INEFFECTIVE (no-op) — matches production "could not find"
  - scoreEvent instr 99: EFFECTIVE — kills all instr 1 voices (runs inside Csound)

Current code  → max_active_voices == 6  → FAIL
Fixed code    → max_active_voices == 3  → PASS

Run:
    python tests/test_chord_stopping.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chords import CHORDS, ChordResult


# ── Simulation ─────────────────────────────────────────────────────────────────

def simulate_active_voices(mock_pt):
    """
    Replay recorded PT calls through a simulation of Csound's actual behavior:

      - inputMessage("i -x 0 0")             → no-op (matches "could not find" logs)
      - scoreEvent("i", pfields) instr==1    → voice starts (+1 active)
      - scoreEvent("i", pfields) instr==99   → ALL instr 1 voices cleared (kill works)

    Returns the maximum number of simultaneously active chord voices.
    """
    active = 0
    max_active = 0

    all_calls = []

    for call in mock_pt.scoreEvent.call_args_list:
        _, opcode, pfields = call.args
        all_calls.append(("score", opcode, pfields))

    for call in mock_pt.inputMessage.call_args_list:
        all_calls.append(("input", call.args[0]))

    # scoreEvent and inputMessage calls are interleaved in call order.
    # Reconstruct by replaying mock_pt calls in the order they were made.
    # (MagicMock preserves call order via method_calls on the parent mock.)
    active = 0
    max_active = 0

    for call in mock_pt.method_calls:
        name = call[0]
        args = call[1]

        if name == "scoreEvent":
            _, opcode, pfields = args
            if opcode != "i":
                continue
            instr = int(pfields[0])
            if instr == 99:
                # Kill instrument: clears all active instr 1 voices (reliable)
                active = 0
            elif instr == 1:
                # New chord voice starts
                active += 1
                max_active = max(max_active, active)

        elif name == "inputMessage":
            # inputMessage with fractional instrument stop: NO-OP in simulation.
            # Matches production log: "could not find playing instr 1.000000"
            pass

    return max_active


# ── Fixtures ───────────────────────────────────────────────────────────────────

def make_chord_result(chord_index=0):
    chord = CHORDS[chord_index]
    return ChordResult(
        numeral=chord.numeral,
        name=chord.name,
        score=0.75,
        all_scores={c.numeral: 0.1 for c in CHORDS},
        midi_notes=chord.midi_notes,
        frequencies=chord.frequencies,
    )


def make_bridge_with_mock():
    """
    Builds a CsoundBridge with ctcsound mocked out.
    Returns (bridge, mock_pt).
    """
    mock_ctcsound = MagicMock()
    mock_pt = MagicMock()
    mock_cs = MagicMock()

    mock_ctcsound.Csound.return_value = mock_cs
    mock_ctcsound.CsoundPerformanceThread.return_value = mock_pt
    mock_cs.compileOrc.return_value = 0

    with patch.dict("sys.modules", {"ctcsound": mock_ctcsound}):
        from csound_bridge import CsoundBridge
        bridge = CsoundBridge()

    return bridge, mock_pt


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_single_chord_starts_exactly_3_voices():
    """Playing one chord must start exactly 3 voices of instr 1."""
    bridge, mock_pt = make_bridge_with_mock()
    mock_pt.reset_mock()

    bridge.play_chord(make_chord_result(0))

    max_active = simulate_active_voices(mock_pt)
    assert max_active == 3, (
        f"Expected 3 active voices after first chord, got {max_active}"
    )
    print("  OK  single chord starts exactly 3 voices")


def test_second_chord_does_not_stack_voices():
    """
    Playing two chords must never exceed 3 simultaneous active voices.

    FAILS with current code (inputMessage stops are no-ops → voices accumulate → 6).
    PASSES once instr 99 (or equivalent internal kill) is used.
    """
    bridge, mock_pt = make_bridge_with_mock()
    mock_pt.reset_mock()

    bridge.play_chord(make_chord_result(0))  # C major
    bridge.play_chord(make_chord_result(5))  # A minor

    max_active = simulate_active_voices(mock_pt)
    assert max_active <= 3, (
        f"Chord voices accumulated: max {max_active} simultaneous voices detected. "
        f"Old voices are not being stopped before new ones start."
    )
    print(f"  OK  two chords: max {max_active} simultaneous voices (no stacking)")


def test_many_chords_do_not_stack_voices():
    """Rapid chord changes must never exceed 3 active voices."""
    bridge, mock_pt = make_bridge_with_mock()
    mock_pt.reset_mock()

    for i in range(7):
        bridge.play_chord(make_chord_result(i))

    max_active = simulate_active_voices(mock_pt)
    assert max_active <= 3, (
        f"After 7 chords: max {max_active} voices — voices are stacking."
    )
    print(f"  OK  7 rapid chords: max {max_active} simultaneous voices")


def test_kill_precedes_starts_in_every_call():
    """
    Within each play_chord call, the kill mechanism must appear BEFORE
    any new instr 1 note starts. If new notes start before the kill,
    they will overlap with the previous chord's notes.
    """
    bridge, mock_pt = make_bridge_with_mock()
    mock_pt.reset_mock()

    bridge.play_chord(make_chord_result(0))
    bridge.play_chord(make_chord_result(3))

    calls = mock_pt.method_calls
    instr1_starts = [i for i, c in enumerate(calls)
                     if c[0] == "scoreEvent" and int(c[1][2][0]) == 1]
    kill_calls = [i for i, c in enumerate(calls)
                  if c[0] == "scoreEvent" and int(c[1][2][0]) == 99]

    assert kill_calls, "No kill event (instr 99) found — missing stop mechanism"

    # Each group of 3 instr 1 starts should be preceded by a kill
    # (The second group of 3 starts must come after the second kill)
    second_group_starts = instr1_starts[3:]  # starts from the second call
    second_kill = kill_calls[-1] if len(kill_calls) >= 2 else kill_calls[0]

    assert all(start > second_kill for start in second_group_starts), (
        "New notes start BEFORE the kill event — old voices will still be playing"
    )
    print("  OK  kill precedes new note starts in every play_chord call")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    tests = [
        ("single chord starts exactly 3 voices",        test_single_chord_starts_exactly_3_voices),
        ("second chord does not stack voices",           test_second_chord_does_not_stack_voices),
        ("many chords do not stack voices",              test_many_chords_do_not_stack_voices),
        ("kill precedes starts in every call",           test_kill_precedes_starts_in_every_call),
    ]

    print(f"\nChord stopping tests\n{'─'*40}")
    failures = []
    for name, fn in tests:
        print(f"\n[{name}]")
        try:
            fn()
        except Exception as exc:
            print(f"  FAIL  {exc}")
            failures.append((name, exc))

    print(f"\n{'─'*40}")
    if failures:
        print(f"FAILED  {len(failures)}/{len(tests)}")
        sys.exit(1)
    else:
        print(f"PASSED  {len(tests)}/{len(tests)}")
        sys.exit(0)


if __name__ == "__main__":
    main()
