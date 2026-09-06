# The no-lex (13,23) census: prediction met

`exist.py 13 23 --backend cadical --no-lex --all-models` (pysat incremental, blocking each found
model on its block variables, canonical row of point 0 and sign anchors kept, NO lex-leader)
wrote `pts-13-23-nolex-labelled.pts`: **184,320 lines, 184,320 distinct labelled models**, exactly
the number PREDICTION.md fixed before the run ended (4 leave-free points x |G0| = 46,080 / |Aut| = 1).
Canonicalised with pynauty on the coloured incidence graph, all 184,320 give the certificate of
the one class in `../pts-13-23-pseudoline.txt` (sha256 bd30d3d2...): 0 outside it, 0 duplicates
(22 s). The closing solver call, which must return UNSAT to certify that no 184,321st model exists,
was still running when this file was written (started about 19:35Z on 2026-09-05); this file is
updated when it returns.
