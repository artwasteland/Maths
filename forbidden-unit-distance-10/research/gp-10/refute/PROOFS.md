# Algebraic helper identities

No new certificate type or AMP move is added, so no contract amendment is
proposed. AMP moves and TU gadgets use the existing trusted proofs in
`research/unit-distance-22/check/PROOFS.md`. The following calculation only
accelerates discovery of certificates already allowed by CONTRACT 3.2.
Every helper is expanded and checked before use; every emitted certificate
contains cofactors of the original frame and saturation system only.

Take a four-cycle `(a,b,c,d)`, and use planar vector coordinates. Put
`A=p_a-p_c`, `B=p_b-p_d`, and `S=p_a+p_c-p_b-p_d`. Write `E_uv=d2(u,v)-1`.
The following polynomial identities follow by expansion:

```
S.A = (E_ab-E_bc-E_cd+E_da)/2
S.B = (-E_ab-E_bc+E_cd+E_da)/2
A.B = (-E_ab+E_bc-E_cd+E_da)/2
```

For each coordinate j, the two dimensional Gram identity is

```
(A.A)*(B.B)*S_j =
 ((B.B)*A_j-(A.B)*B_j)*(S.A)
 + ((A.A)*B_j-(A.B)*A_j)*(S.B)
 + (A.B)*S_j*(A.B).
```

For each diagonal choose an inverse t with `t*d2-1` among the generators.
If that diagonal is already an edge, use t=1 and its edge generator.
If it is the framed edge, that generator is identically zero and is omitted.
Call the two inverses ta and tb, and their generator identities Ca and Cb.
Multiplying the Gram identity by ta*tb and subtracting
`S_j*Ca + ta*(A.A)*S_j*Cb` gives S_j itself. Substituting the displayed edge
combinations supplies its exact cofactor certificate.

Singular may use these linear S_j helpers along with the original
polynomials. If it returns an identity for a target, substitute the stored
cofactor expression for each helper and expand the resulting identity in
python-flint. This proves membership in the original ideal. It makes no
claim about complex injectivity or isotropic differences.

For R-null, the target one rules out every zero of the chosen system.
For R-real, an exact zero-free univariate polynomial or an expanded positive
constant plus positive weighted squares rules out every real zero. In a
real injective embedding all saturated squared distances are positive, so
L-frame and L-sat justify applying these certificates to the input graph.

Framing a nonedge is forbidden even if that particular additional distance
constraint happens to admit an embedding. Invalid framing need not produce
a unit ideal for every embeddable graph. The frame guard is checked directly
with a one-field mutation on the pentagonal prism in selftest.py.

## Deliberately wrong prism frame

Use the usual prism labels with cycles `(0,1,2,3,4)` and `(5,6,7,8,9)`
and matching edges `(i,i+5)`. Incorrectly imposing unit length on nonedge
`(0,7)` creates a four-cycle `(0,1,2,7)`. Its rhombus equation says
`p0+p2=p1+p7`. The genuine four-cycle `(1,2,7,6)` says
`p1+p7=p2+p6`. Thus p0=p6, contradicting injectivity. Saturating that
squared distance permits a unit-ideal certificate for the wrongly framed
system. This is a demonstration of the framing bug, never an allowed move.

For the positive control, theta=sin(72 degrees) satisfies
`16*theta^4-20*theta^2+5=0` in the interval `(95/100,96/100)`. The script
constructs a regular unit pentagon using its exact four-dimensional power
basis, rotates its coordinates, and translates a copy by `(1,0)`. The
trusted embedding kernel verifies every edge exactly; field signs verify
strict positivity of every squared pair distance. A coincident-coordinate
mutation is rejected. All saturation inverses exist in this real field.
Only the frame field is then changed. The guard rejects it, while an
explicitly disabled guard produces an exact false-refutation identity.
These coordinates are solely a refuter safety fixture and do not count as
an embedding producer's general-search named control.

## Round 2: compiling zero sums of squares into R-real

This is a producer construction within the existing R-real grammar, not a new
checker move. Let I be the regenerated edge/saturation ideal. Suppose exact
cofactor expansion proves S = sum_i w_i q_i^2 belongs to I, with rational w_i > 0.
Suppose a second exact lift proves 1 = A + sum_i q_i h_i, where A belongs to I.
Set Q = sum_i q_i h_i and T = sum_i h_i^2/w_i. The weighted Lagrange identity is

    S*T - Q^2 = sum_(i<j) (w_i/w_j)*(q_i*h_j - (w_j/w_i)*q_j*h_i)^2.

Since Q = 1-A, it follows that

    1 + sum_(i<j) (w_i/w_j)*(q_i*h_j - (w_j/w_i)*q_j*h_i)^2
        = S*T + A*(2-A) in I.

Multiplying the known cofactors of S by T and those of A by 2-A produces the
cofactors of this strictly positive polynomial. The official checker only needs
its existing expansion and positive-weight SOS checks. The temporary equations
q_i=0 never appear as unverified generators in the emitted certificate.

For F(9,14,2), the three path vectors from picture vertices 1 to 8 to 9 to 6
are compared to p3-p1. Four rhombus relations give p6-p1 = 3*(p3-p1), and all
four relevant vectors have unit length. Thus the sum of their three squared
vector differences is zero. The corrected edge 3--4 in the picture is verified
against the frozen graph by an explicit isomorphism before use.

For F(9,14,18), the candidate zero SOS is twice the sum of squared deviations
of p9 from (p1+p7)/2 and p8 from (p5+p4)/2. The parallelogram argument in GP
suggests this polynomial. Its membership in the original ideal is independently
required by an exact lift and expansion, so a mistaken picture or interpretation
cannot yield an accepted certificate.

### Exact linear preprocessing

For a common neighbor v of the framed edge (a,b), subtracting its two edge
polynomials gives E(a,v)-E(b,v)=2*x_v-1. This is an exact ideal identity.
Rational row operations on these and the certified rhombus equations preserve
an explicit cofactor representation. Polynomial division by such a row h
replaces p by p-q*h, with its cofactors changed by subtracting q times h's
cofactors. Every transformed polynomial is expanded against the original
regenerated generators before CAS use. This changes discovery cost only.

### Factored saturation lifts

Let d_i be selected squared distances, s_i=t_i*d_i-1, D=product_i d_i,
T=product_i t_i, and Z=T*D. If a lift proves f*D^k=sum_j a_j*g_j using a
smaller set of already certified generators, then

    f = T^k*sum_j a_j*g_j - f*(Z^k-1).

The telescoping identities

    Z-1 = sum_i s_i*product_(j<i)(t_j*d_j),
    Z^k-1 = (Z-1)*(1+Z+...+Z^(k-1))

expand the second term using only the original saturation generators. This
can reduce discovery and certificate size. Every final identity is expanded
exactly and checked by the existing R-null or R-real branch.

### Homogeneous discovery lifts

A temporary homogenizing variable h can be used by the producer to restrict
cofactor degree. A homogeneous polynomial identity remains an identity after
substitution h=1. The wrapper performs that substitution in every cofactor,
then re-expands the identity in the original ring. No h variable or extra
generator is emitted or accepted by the checker. Failed homogeneous membership
is simply an unsuccessful search, even if the unhomogenized target belongs
to the ideal. Singular's documented lift algorithm choices are std and slimgb:
[upstream reference](https://raw.githubusercontent.com/Singular/Singular/spielwiese/doc/reference.doc).

For F9 index 66, the low-degree candidate is
2 + (|sum_(i=0,1,2) p_i - sum_(i=3,4,5) p_i|^2)/3 in canonical labels.
It has constant 2 and two rationally weighted coordinate squares. The two
triangles suggest the candidate; only the expanded ideal identity certifies it.

### Two-circle branch polynomials

Let A,B be centres, P and R be points, Q=A+B-P, D=B-A, N=(-D_y,D_x),
X=R-P, Y=R-Q, and d=D dot D. Define E(T,C)=|T-C|^2-1.
Then the following are exact polynomial identities:

    L=D dot X=(E(R,A)-E(R,B)-E(P,A)+E(P,B))/2,
    K=D dot Y=(E(R,A)-E(R,B)+E(P,A)-E(P,B))/2,
    M=X dot Y=(E(R,A)+E(R,B)-E(P,A)-E(P,B))/2,
    d*X_i*Y_j=N_i*N_j*M+D_i*Y_j*L+D_j*X_i*K-delta_ij*L*K.

If the four E polynomials have known ideal cofactors and t*d-1 is a
regenerated saturation generator, multiplication by t and subtraction of
(t*d-1)*X_i*Y_j give exact cofactors for each quadratic X_i*Y_j. These are
producer helpers, never extra checker generators.

For F9 index 39 in canonical labels, use A=p6, B=p7, R=p5, z=p8,
q=p1, b=p4, r=p2, s=p3, P=q+s-z. Rhombus equations give A=q+b-z and
B=r+s-z. Therefore E(P,A) and E(P,B) are obtained from the actual unit
edges b--s and q--r plus explicitly tracked rhombus corrections. The
saturation pair of the two centres is (6,7). Every helper is independently
expanded in the original ideal before use in a lift.

### Compiling the two cases for F9 index 39

Write P=q+s-z, Q=r+b-z, X=W-P and Y=W-Q in the labels above. The
first circle identity, with tracked rhombus corrections, proves every
X_i*Y_j belongs to the original ideal I. In the branch X=0, applying the
same circle identity to centres z,W, known solution q and actual solution V
proves F_A=|V-q|^2*|V-s|^2 belongs to I+(X_x,X_y). In the other branch,
F_B=|V-r|^2*|V-b|^2 belongs to I+(Y_x,Y_y).

Retain identities F_A=A+sum_i a_i X_i and F_B=B+sum_j b_j Y_j, with
A,B in I. Then

    F_A*F_B = A*F_B + B*(F_A-A) + sum_(i,j) a_i*b_j*X_i*Y_j in I.

Finally multiply by the four corresponding saturation variables. Subtract
the telescoping identity product(t_i*d_i)-1, expressed in the four original
saturation equations, to obtain 1 in I. All intermediate and final identities
are verified by exact polynomial expansion. The branches are a producer
construction; no branch node or new generator reaches the checker.

### Cofactor reduction

If h_i=q*g_j+r in a cofactor identity, replace h_i by r and h_j by
h_j+q*g_i. The represented sum is unchanged because multiplication commutes.
The producer may use these Koszul syzygies to reduce sparse certificate size;
the final checker still receives and expands only ordinary cofactor polynomials.

## Proposed amendment: explicit intermediate ideal identities

This is a proposal, not an accepted certificate type. No production record
uses it. The companion `39-ideal-derivation.json` is an auxiliary derivation
document without a verdict or certificate type.

Let the checker regenerate the edge-frame ideal generators G as for R-null.
A row consists of a polynomial p and a finite dictionary of polynomial
coefficients indexed by original generators or earlier rows. Require the
exact identity p = sum(a_i q_i), where every q_i is an original generator
or a strictly earlier row. The last row must be the constant one.

Soundness follows by induction: every original generator belongs to I;
every checked row is a polynomial combination of elements already in I;
therefore every row belongs to I. A last row equal to one proves I is the
whole ring. This is the same Nullstellensatz argument as R-null. It adds
shared intermediate polynomials to the encoding, not a geometric premise.
Flattening the rows yields an ordinary R-null identity, but can enlarge its
serialized coefficients substantially.

Suggested contract name: R-null-dag, with proposed `type: "null-dag"` and
fields `frame`, `sat`, and `rows`. Each row has exactly `poly` and
`cofactors`; original-generator keys retain their existing meaning and
`aux:j` refers to the zero-based prior row j. The checker must reject
forward references, missing sources, cycles, extra fields, malformed or
noncanonical sparse terms, and any failed exact identity. It must enforce
the existing edge-only frame and saturation rules, the existing rational
coefficient and polynomial-variable rules, a positive finite row budget,
the existing byte and arithmetic resource limits, and final polynomial 1.
Suggested initial row cap: 256. Exhaustion is rejection or unknown, never
acceptance. The official checker needs its own implementation; the local
prototype is not a replacement for independent checking.

For index 39 the derivation first proves the four rhombus coordinate
relations. It then proves each substituted generator by a telescoping
polynomial substitution identity. The final row combines those generators
using the independently expanded two-circle branch calculation above.
The quotient compression is exact: reduce selected coefficients modulo
locally proved ideal elements, then rebuild the discarded coefficients by
reducing the complete residual. Every resulting equality is expanded and
checked, so neither an assumed Groebner basis nor a normal-form uniqueness
claim is needed for soundness.

## Round 3: amendment 5 adopted

The contract and the independent checker now accept null-dag and real-dag.
The former proposal above is historical. Producers use strictly increasing
lexicographic exponent vectors with no zero terms, the binding checker
format, and at most 256 rows. The generic search records each exact
preprocessing identity as a row, then records the exact lift as a final
combination of those rows. The induction in shared PROOFS.md Section 6
proves soundness. Every emitted identity is expanded locally and must also
pass the official checker before it is counted. CAS output remains only
a discovery aid. No new geometric lemma is introduced in this round.

### Targeted collision saturation

Let J be the current framed, saturated edge ideal. If an exact checked
identity proves d2(u,v) belongs to J for a nonedge not yet saturated, extend
the ring by t and append t*d2(u,v)-1. The earlier identities remain valid
in the extended ring. One final row is t times the proved distance row
minus the new saturation generator, exactly 1. L-sat and amendment 5 then
prove non-embeddability. A Groebner remainder of zero is only a discovery
hint: the producer must obtain and expand an identity in original
generators before emitting the distance row. No CAS membership assertion
is trusted.

### Quadratic SOS discovery inside the existing ideal

Linear programming is used only to suggest rational coefficients for an
identity f = sum(lambda_i b_i) = 1 + sum(w_j q_j^2), where b_i are
quadratic basis elements or monomial multiples of linear basis elements,
and w_j are nonnegative. Both equalities are checked exactly after rational
reconstruction; zero weights are removed. A separate exact CAS lift and
its expanded original-generator or DAG identities are still required.
The final positive constant and strictly positive remaining weights use
the existing R-real rule. Numerical feasibility alone never emits a
certificate. Coordinate differences and differences of triangle vertex
sums supply candidate linear q_j, with no geometric assumption attached
to those choices. The basis membership assertion is not trusted.

## Round 4: two-edge-path SOS targets

For edges uw and vw, write Eab = ||p(a)-p(b)||^2 - 1 and
Duv = ||p(u)-p(v)||^2. Direct expansion gives

2 Euw + 2 Evw = Duv - 4 + ||p(u)+p(v)-2p(w)||^2.

If an independently lifted ideal identity forces Duv = d with rational
d > 4, subtraction gives the strictly positive ideal element
(d-4) + ||p(u)+p(v)-2p(w)||^2. This is an existing R-real SOS
certificate, with no new move or trusted inequality. Adding the two
coordinate forms p(u)+p(v)-2p(w) to the discovery dictionary can also
find combinations of these identities. Every numerical proposal must
pass exact rational reconstruction, exact lifting and the independent
checker. A hint about distance or collision is never a proof premise.

Saturating a suggested non-edge collision pair is sound by L-sat whether
or not the hint is accurate. Its vertex labels are checked against the
canonical graph, and a wrong suggestion can only make search less useful.
