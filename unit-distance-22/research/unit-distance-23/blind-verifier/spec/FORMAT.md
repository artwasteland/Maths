# Certificate format (verbatim: the module docstring of the reference checker, which you must NOT read)

Independent certificate checker for the u(22) programme.

Certificate witness schema
==========================

All polynomial coefficient arrays are in ascending order.  Exact rational
numbers are JSON integers or strings such as ``"-7/12"``.  A real field is
represented by::

    {"minpoly": [c0, c1, ..., cd], "interval": [left, right]}

It denotes the unique real root alpha of the irreducible polynomial in the
open rational interval.  A field element is an array ``[q0, ..., q_(d-1)]``
representing sum(q_i alpha^i).  A complex field element is either a real
field element, a rational scalar, or ``{"re": element, "im": element}``.

An embedded witness has keys ``field`` and ``coordinates``.  Coordinates are
``[x,y]`` pairs of real field elements.

A refuted witness has keys ``field`` and ``tree``.  Every tree node contains
``edges``, ``A``, ``move`` and ``children``.  A is a matrix of complex field
elements.  The move forms are::

    {"kind":"L1a", "pair":[u,v]}
    {"kind":"L1b", "edges":[[u,v],[x,y]], "omega": complex}
    {"kind":"L1c", "edges":[[u,v],[x,y],[p,q]], "coefficients":[a,b,c]}
    {"kind":"L2",  "edges":[[u,v],[x,y]], "omega": complex}
    {"kind":"L3",  "edges":[[u,v],[x,y],[p,q]],
                       "coefficients":[a,b,c], "d": element}

L1 nodes have no children, L2 has one child, and L3 has two ordered children.
The first L3 child gets the +i*d equation and the second gets the -i*d one.

Lemma 4, in our own words
-------------------------

Suppose three unit complex displacements x, y, z obey ax+by+cz=0.
The three complex vectors ax, by and cz form a possibly degenerate triangle.
Writing q=|a|^2+|b|^2-|c|^2 and
d^2=4|a|^2|b|^2-q^2, the law of cosines leaves exactly the two orientations
of that triangle.  Consequently either
    (q+i*d)*a*x + 2|a|^2*b*y = 0
or the same equation with -i*d holds.  These two equations cover all cases.
At every L3 node this checker independently verifies ax+by+cz is in the row
space of A, verifies d^2 exactly, checks d is real at the selected root, and
checks that the two child row spaces are precisely A plus the two equations.

No floating point arithmetic is used for a trusted decision.  Polynomial
reduction, field arithmetic, row reduction, and root isolation are performed
below with fractions.  SymPy is used only to test irreducibility over Q.
