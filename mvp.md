MVP

Start with the 7 diatonic chords in a fixed key (I, ii, iii, IV, V, vi, vii°).

Do a deep analysis of how each chord feels. Take from existing sources:
    sources of feeling, music phenomenology, everything that gets at how we view the emotional character of each chord.

Turn that into a report where each of the 7 chords has a page worth of keywords
(the kind of thing we can use to unflatten embedding vector space into these 7 emotional qualities)

Do the embeddings magic. 
Output: I can give you any text, and you tell me what chord should play

This is the base to bring into Cursor (Csound IDE of choice), let's make it sound good!

Optimize the code for:
Ability to build on this. One chord becomes a progression. Chord becomes soundscape.
Soon, we'll make a text edtior, where we can write a line then hit enter, and then the chord of that line plays.

Structure which allows me to influence how the embeddings are done, do this by creating:
Infrastructure docs (atomic docs which lays out how one particular process is done,
we can change the doc, rerun, and you'll recode it so that the doc is used to intelligently rewrite the code)
