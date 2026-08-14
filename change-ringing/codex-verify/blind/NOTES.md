# Interpretation and derivation notes

I treated a permutation as a row of five positions.  If a bell moves by at
most one place, the map from old positions to new positions is a permutation
of `1,...,5` in which every position moves by 0 or 1.  Such a map consists
exactly of disjoint adjacent transpositions.  Thus a transition may swap any
set of non-touching gaps among `12, 23, 34, 45`.  The eight possible sets are

```
none, 12, 23, 34, 45, 12+34, 12+45, 23+45.
```

The empty set is the identity move.  Away from the closing row it would
immediately repeat a permutation and is therefore forbidden by criterion 2.
There are consequently seven usable edges out of every permutation.  For the
special repeated starting row at the end, the identity move is relevant to
the two-row cyclic sequence under the literal length reading.

The path count includes sequences starting at `12345` whose final row is not
`12345`.  Since every visited row is otherwise distinct, this is the number
of rooted simple paths with `L` vertices.  In particular the length-one path
count is zero: its final row equals its starting row, so it satisfies rather
than "does not satisfy" criterion 4.

## Cyclic length ambiguity

I printed both readings because the definition is internally tense:

* `cyclic_count_including_close` follows the explicit footnote literally:
  length is the number of permutations in the sequence, including a repeated
  starting permutation written at the end.  At `L=1`, `[12345]` already
  starts and ends at the same row, so the count is 1.  At `L=2`,
  `[12345,12345]` is allowed: the start is repeated once at the end and every
  bell stays in place.  Hence this column also has value 1 at `L=2`.
* `cyclic_count_excluding_close` treats `L` as the number of distinct rows,
  with the final copy of `12345` implicit and not charged to the length.  At
  `L=1`, the implicit identity closure gives 1.  At `L=2`, any one of the
  seven nonidentity moves can be followed by its inverse (itself), giving 7.

The first reading is the more direct consequence of “the number of
permutations in the sequence.”  The second reading explains the later claim
that the maximum length is `5! = 120`: if an explicit repeated closing row
were counted, a full cycle could contain 121 written permutations.  Rather
than silently resolve that contradiction, `enum.c` computes both columns.
For `L >= 2`, the including-close value at `L+1` equals the excluding-close
value at `L`, as a useful internal check.

## Enumeration and checks

`enum.c` builds all 120 permutations and their seven legal nonidentity
neighbors, then performs a direct depth-first enumeration from `12345` with a
120-bit visited set.  It does not use published values or external data.
All requested lengths through 13 completed comfortably inside the three
minute limit using the requested optimized, single-threaded invocation.

Sanity checks visible in the output include path counts 0 and 7 at lengths 1
and 2, the two tiny cyclic cases above, and the one-column shift relation
between the cyclic readings.
