#!/usr/bin/env python3
"""Play a brief low I chord — called by the Claude stop hook."""
import sys
import time


def main():
    try:
        import ctcsound
    except ImportError:
        sys.exit(0)

    orc = """
sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1
    kenv  linseg   0, 0.5, 1, 0.5, 0.85, 0.5, 0
    a1    oscili   p4 * kenv, p5
    a2    oscili   p4 * kenv * 0.6, p5 * 1.004
    a3    oscili   p4 * kenv * 0.3, p5 * 2.0
    aout  = a1 + a2 + a3
    outs  aout, aout
endin
"""
    # I chord, octave 3: C3, E3, G3
    freqs = [130.81, 164.81, 196.00]

    cs = ctcsound.Csound()
    cs.setOption("-odac")
    cs.setOption("-d")
    cs.compileOrc(orc)

    score = "\n".join(f"i 1 0 1.5 0.07 {f}" for f in freqs) + "\ne 2.0\n"
    cs.readScore(score)
    cs.start()

    pt = ctcsound.CsoundPerformanceThread(cs.csound())
    pt.play()
    # Wait for score to finish naturally — no abrupt stop
    while pt.status() == 0:
        time.sleep(0.05)
    pt.join()
    cs.cleanup()
    cs.reset()


if __name__ == "__main__":
    main()
