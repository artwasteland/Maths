# Prediction for the no-lex (13,23) census, written BEFORE the run finished

Written 2026-09-05 18:15Z by claude-reaching-noether-7e1c, while `exist.py 13 23 --backend cadical
--no-lex --all-models` stood at about 135,000 block assignments (run.log), so that the census ends
against a number fixed in advance.

The lex census found 441 labelled models, all one isomorphism class P (pts-13-23-pseudoline.txt,
sha256 bd30d3d2...). If P is the only pseudoline-admitting PTS(13,23), then the no-lex census,
which keeps the canonical row of point 0 and the sign anchors but no lex-leader, and blocks each
found model on its block variables, must find exactly

    m * |G0| / |Aut(P)| = 4 * 46080 / 1 = 184,320 labelled models,

where m = 4 is the number of points of P with leave degree 0 (its leave is a 2-regular graph on
9 points plus 4 isolated points, so r2min = 0 and any of the 4 isolated points can be point 0),
G0 = Z2 wr S6 of order 46,080 is the group of relabellings that preserve the canonical row
{0,1,2}, {0,3,4}, ..., {0,11,12} (each of the other 12 points lies in point 0's row, so a
labelling is determined by the row's labelling), and |Aut(P)| = 1 (pynauty on the coloured
incidence graph). Every model must canonicalise (realize/canonicalize.py) to P.

- More than 184,320, or any model outside P: a second class exists and the lex-leader of the
  lex census was unsound; t3(13) = 22 then rests on stage 3 refuting that class too.
- Fewer than 184,320: the blocking or the anchors over-constrain; the census is not a census.
- Exactly 184,320, all in P: the control passes and the t3(13) = 22 certificate is unconditional.
