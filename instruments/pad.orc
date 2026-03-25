; pad.orc — Simple pad instrument for chord sonification
; p4 = amplitude (0.0–1.0)
; p5 = frequency in Hz

sr     = 44100
ksmps  = 32
nchnls = 2
0dbfs  = 1

instr 1
    kenv  linsegr  0, 0.05, 1, p3 - 0.1, 0.8, 0.05, 0
    aout  oscili   p4 * kenv, p5
    outs  aout, aout
endin
