The following describes the accepted refutation records. The records and frozen-checker receipts are the proof authority; the elimination computations alone were discovery tools.

`JaICZOo@Wd_`: use the ordered edge frame (8,10), placing p8=(0,0) and p10=(1,0). Write h=y9. The rhombi and shared equilateral triangles imply

- h²=3/4, p9=(1/2,h), p3=(1/2,-h);
- p2=p7-(1/2,h), p5=p6+(-1/2,h);
- p0=p6+(-1,0) or p6+(1/2,h);
- p4=p7+(-1,0) or p7+(1/2,-h).

Let e and b be the choices in the last two lines, with the first option numbered zero. All four combinations are retained. The proof uses saturation pairs (2,9), (3,9), (5,10), (6,9), (7,8), (0,4), (1,5), (2,3), (2,6), (2,10), (7,10). The first five justify the rhombus reductions; the rest are exactly the additional distinctness equations used by the combined argument.

| (e,b) | Further algebraic conclusion | Pairs used in the final saturation step within the branch |
|---|---|---|
| (0,0) | Q4(y0)=0 | (5,10), (6,9), (2,3), (0,4) |
| (0,1) | 1=0 | (7,8), (6,9), (1,5), (7,10), (2,10) |
| (1,0) | Q8(y0)=0 | (7,8), (2,3), (2,6), (0,4) |
| (1,1) | 1=0 | (7,8), (2,6), (1,5) |

Here

    Q4(z) = 196*z^4 + 189*z^2 + 144
    Q8(z) = 362404*z^8 - 1633527*z^6 + 2319417*z^4 - 97632*z^2 + 20736.

The quartic is visibly positive. The frozen checker's exact Sturm calculation proves that Q4*Q8 has no real root, covering the octic as well.

The branch proof does not pin any unauthorized coordinate. Put s0=(4/3)*h*(y0-y6) and s4=-(4/3)*h*(y4-y7). The triangle equations prove s0 and s4 are zero or one. The four polynomial selectors (1-s0)(1-s4), (1-s0)s4, s0(1-s4), and s0*s4 sum identically to one. The certificate proves that each selector annihilates its branch assumptions, derives that selector times Q4*Q8, then adds the four identities. The final polynomial is Q4(y0)*Q8(y0)/71031184. It is checked with `sturm: y_0`.

A geometric intermediate hint was the restriction y7 in {0,h,2h}: elimination gives, after writing y7=h*z, a factor proportional to

    z^3*(z-2)*(z-1)*(7*z^2+4)*(7*z^2+7*z+2).

The last two factors have no real roots. In the y7=h, x7=-1/2 branch, avoiding p4=p8 forces p4=(-3/2,h). Then p4 and p10 are distance sqrt(7) apart although p6 would have to be one unit from both. This explains one real obstruction, but the accepted certificate uses the four exhaustive triangle cases above to cover every possibility.

`JSO@]OSDjB?`: use the ordered edge frame (8,9), placing p8=(0,0), p9=(1,0). The rigid triangular patch has p3=(1/2,-h), p5=(1/2,h), p6=(3/2,h), h²=3/4. The other rhombi give p0=p2+p7-p10 and p1=p4-p7+p10. Saturation uses (0,10), (2,7), (3,5), (4,10), (6,8), (2,5).

Let D=|p2-p7|²*|p2-p5|². Reduction of the coordinate equations yields D*P(x0)=0, where

    P(x) = (2*x^2-5*x+5)
           *(7*x^2-21*x+18)
           *(1024*x^6-4224*x^5+6672*x^4-3040*x^3-2412*x^2+2142*x+837)
           *(2048*x^8-14080*x^7+39648*x^6-55168*x^5+32000*x^4
             +7104*x^3-16416*x^2+2511*x+2754).

The saturation equations invert D and give P(x0)=0. The frozen checker verifies that P has no real root by an exact Sturm calculation. Its final target is P/29360128, checked with `sturm: x_0`. Staged low-degree identities and Horner remainders keep the derivation within the certificate size limit.

Both records are `real-dag` certificates. Every row is an exact polynomial linear combination of original edge equations, injectivity saturation equations, and earlier rows. The checker independently regenerates that system; it does not trust Singular, the branch enumeration, a numerical candidate, or a claimed Groebner basis.

The accepted receipts are `check-A.log`, `check-B.log`, and the corresponding `check-A/checked/report.json` and `check-B/checked/report.json`. The certificate hashes are:

    A: 90aa0abd0b81a64053b3d125865ec7b742add21ed1728c3993c2af3b2a01fd41
    B: ef63d3a0eab4625bbf13f3da2bd7d3402e905daae7eef188003a98f37a37afc0

Replay from any directory, retaining all scratch writes inside the authorized directory:

```bash
export SYMPY_GROUND_TYPES=python PYTHONDONTWRITEBYTECODE=1
<repo>/pyenv-gp10/bin/python /tmp/gp11-analyst-A1/guard.py replay-A 120 <repo>/pyenv-gp10/bin/python /tmp/gp11-analyst-A1/check_record.py /tmp/gp11-analyst-A1/records/A-real-dag.jsonl A-replay
<repo>/pyenv-gp10/bin/python /tmp/gp11-analyst-A1/guard.py replay-B 120 <repo>/pyenv-gp10/bin/python /tmp/gp11-analyst-A1/check_record.py /tmp/gp11-analyst-A1/records/B-real-dag.jsonl B-replay
```

The wrapper imports the original frozen checker and changes only its runtime SCRATCH directory. The source hash remains d717816bde784fae3314e2c73dbc85f0e786a753f776429d61ba17a4ddeeaf04. The retained producers are `build_A.py` and `build_B.py`; their inputs and all bounded-attempt metadata remain alongside them.
