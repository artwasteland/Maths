# Proofs for the six TU gadgets

All vertex numbers below are exactly the numbers in data/tu-gadgets.json.
Write \(p_i\) for the point assigned to vertex \(i\) by an arbitrary
unit-distance embedding.

## Two geometric facts

Every 3-cycle is an equilateral triangle. Its three sides have length one, so
the cosine rule gives an angle of \(\pi/3\) at every vertex.

Every 4-cycle is a rhombus, including the conclusion needed here that its
diagonals have a common midpoint. Thus, for a cycle
\((a,b,c,d)\) in cyclic order,

\[
R(a,b,c,d):=p_a-p_b+p_c-p_d=0.
\]

This remains valid without assuming that the embedding is faithful. It also
does not matter whether a 4-cycle has chords. One way to see the statement
without relying on its picture is to regard its four directed sides as four
unit complex numbers with sum zero. Four points on the unit circle whose
vector sum is zero occur in opposite pairs. Pairing two consecutive sides as
opposites would make two cycle vertices collide, which injectivity forbids.
The opposite sides of the cycle are therefore opposite vectors, which gives
the displayed equation.

## Proof-tree Heron moves L3 and L1c

At a proof-tree node, let $A$ be the current constraint matrix and let
$x,y,z$ be the unit displacements on three directed edges of the current
graph. If $a,b,c\ne0$ are complex elements of the node's real number field
and the row representing

\[
ax+by+cz=0
\]

lies in the row space of $A$, then every unit-distance embedding
$f\in\ker A$ satisfies this relation. Thus $ax,by,cz$ are the directed
sides of a possibly degenerate triangle with side lengths
$|a|,|b|,|c|$. The Heron-esque lemma in the AMP paper
(`sources/amp/erdos_unit_distance_problem.tex`, Lemma `lem.heron-esque`)
therefore gives a real $d$ with

\[
d^2=4|a|^2|b|^2-
\bigl(|a|^2+|b|^2-|c|^2\bigr)^2\ge0.
\]

The L3 move handles the nonnegative case by adjoining the two possible
orientation equations as its two ordered children. The L1c move is the
contradiction leaf

```json
{"kind":"L1c","edges":[[u,v],[x,y],[p,q]],"coefficients":[a,b,c]}
```

with no children. The checker verifies that all three directed edges are
present, all three coefficients are nonzero, the displayed relation lies in
the row space of $A$, and the discriminant is strictly negative at the
selected real root using exact field arithmetic. Strict negativity
contradicts the real square $d^2\ge0$, so no unit-distance embedding in
$\ker A$ exists and the node is refuted outright.

For completeness, the gadgets really do have unit-distance embeddings.
Put \(s=\sqrt 3\), and define the following three coordinate diagrams:

\[
\begin{aligned}
D_0={}&((0,0),(1,0),(1/2,s/2),(0,1),(1,1),(1/2,1+s/2)),\\
D_1={}&((0,0),(1,0),(1/2,s/2),(3/2,s/2),(-1/2,s/2),(0,s),(1,s)),\\
D_2={}&((0,0),(1,0),(1/2,s/2),(3/2,s/2),(0,1),(1,1),
        (1/2,1+s/2),(3/2,1+s/2)).
\end{aligned}
\]

The following maps send each data vertex to a coordinate index in the named
diagram:

| gadget | diagram | map of data vertices |
|---:|:---:|:---|
| 0 | \(D_0\) | \(0:0,1:3,2:5,3:2,4:1,5:4\) |
| 1 | \(D_1\) | \(0:5,1:0,2:2,3:4,4:6,5:3,6:1\) |
| 2 | \(D_1\) | \(0:1,1:4,2:2,3:0,4:3,5:6,6:5\) |
| 3 | \(D_2\) | \(0:0,1:4,2:2,3:6,4:7,5:3,6:1,7:5\) |
| 4 | \(D_2\) | the same map as gadget 3 |
| 5 | \(D_2\) | the same map as gadget 3 |

Direct subtraction checks that every listed gadget edge has length one.
Gadget 5 simply omits one edge of gadgets 3 and 4. The many 3-cycles in these
coordinates are the equilateral triangles described above. These coordinates
establish existence. The arguments below establish the much more important
universal forcing statement.

## Gadget 0

The cycles \((0,1,2,3)\) and \((2,3,4,5)\) give two rhombus equations.
Their difference is

\[
-R(0,1,2,3)+R(2,3,4,5)
=(p_1-p_5)-(p_0-p_4)=0.
\]

Therefore the distinguished displacement \(p_1-p_5\) equals the displacement
of the existing edge \(04\). Its length is one.

## Gadget 1

Use the four cycles

\[
C_1=(0,2,1,3),\quad C_2=(0,3,2,4),\quad
C_3=(1,3,2,6),\quad C_4=(1,2,5,6).
\]

Adding their rhombus equations with coefficients \(0,-1,1,-1\) gives

\[
-R(C_2)+R(C_3)-R(C_4)
=(p_4-p_5)-(p_0-p_2)=0.
\]

The distinguished displacement \(p_4-p_5\) equals the displacement of edge
\(02\), so it has length one.

## Gadget 2

Here use

\[
C_1=(0,2,1,3),\quad C_2=(0,2,5,4),\quad
C_3=(1,3,2,6),\quad C_4=(1,2,5,6).
\]

The combination with coefficients \(-1,1,1,-1\) is

\[
-R(C_1)+R(C_2)+R(C_3)-R(C_4)
=(p_2-p_4)-(p_1-p_2)=0.
\]

Thus the distinguished displacement \(p_2-p_4\) equals the displacement of
edge \(12\), and its length is one.

## Gadget 3

Set

\[
C_1=(0,1,3,2),\quad C_2=(0,2,5,6),\quad
C_3=(1,3,4,7),\quad C_4=(2,3,4,5).
\]

All four are cycles in the gadget. The combination with coefficients
\(1,-1,1,-1\) gives

\[
R(C_1)-R(C_2)+R(C_3)-R(C_4)
=(p_3-p_7)-(p_2-p_6)=0.
\]

Hence the distinguished displacement \(p_3-p_7\) equals the displacement of
edge \(26\), so it has length one.

## Gadget 4

Use the same four cycles as for gadget 3. The combination with coefficients
\(0,-1,1,-1\) gives

\[
-R(C_2)+R(C_3)-R(C_4)
=(p_6-p_7)-(p_0-p_1)=0.
\]

The distinguished displacement \(p_6-p_7\) equals the displacement of edge
\(01\), so it has length one.

## Gadget 5

This gadget lacks edge \(26\), the extra cross edge present in gadgets 3 and
4. None of the cycles \(C_2,C_3,C_4\) used in the gadget 4 proof contains
that edge. They are still cycles in gadget 5, and the identical calculation
gives

\[
(p_6-p_7)-(p_0-p_1)=0.
\]

Thus the distinguished pair again has the same displacement length as edge
\(01\), namely one. This also makes explicit why the cross edge is
unnecessary.

## Conclusion

Each data gadget has an embedding, and in every embedding its stored
non-adjacent pair is forced to unit distance. The proofs only use edge
constraints actually present at the corresponding gadget index. There is no
unproved rigidity assumption and no appeal to numerical coordinates in the
universal part of the argument.
