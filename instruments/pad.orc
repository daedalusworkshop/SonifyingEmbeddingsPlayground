; pad.orc — Simple pad instrument for chord sonification
; p4 = amplitude (0.0–1.0)
; p5 = frequency in Hz

sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1
    kenv   linsegr  0, 0.3, 1, p3 - 0.4, 0.85, 0.1, 0
    a1     oscili   p4 * kenv, p5
    a2     oscili   p4 * kenv * 0.6, p5 * 1.004   ; slightly detuned for chorus
    a3     oscili   p4 * kenv * 0.3, p5 * 2.0      ; octave up, quiet
    aout   = a1 + a2 + a3
    outs   aout, aout
endin

; instr 2 — tonic drone (C4, runs continuously, not killed by chord changes)
instr 2
    kenv  linseg   0, 0.5, 1
    aout  oscili   p4 * kenv, p5
    outs  aout, aout
endin

; instr 99 — kill all 3 chord voices before starting a new chord.
; turnoff2 runs inside Csound and reliably finds active instr 1 instances,
; unlike external inputMessage which produces "could not find" warnings.
instr 99
    turnoff2 1, 4, 1  ; stop oldest instr 1, allow release — call 3× for 3 voices
    turnoff2 1, 4, 1
    turnoff2 1, 4, 1
    turnoff
endin
