# orbits.g: an independent check of the cube split's orbit decomposition, in GAP, from the
# definition alone (nothing here is read from exist.py).
#
# Frame: point 0's row is fixed to its canonical form: the blocks {0,2i-1,2i}, i = 1..r, and
# the remaining points are point 0's leave. G1 is the subgroup of Sym(points) that fixes 0, 1,
# 2 and preserves the row-0 partition M0 = {{3,4},{5,6},...} as a set of sets (the leave points
# are fixed pointwise when there is one, and permuted freely when there are several, exactly
# as the stabiliser of the set of sets gives). A row-1 configuration is the set of blocks of
# point 1 other than {0,1,2}: a matching M of 2*(r1-1) of the remaining points avoiding every
# M0 pair (the points M leaves out are point 1's leave). The claim under test: the G1-orbits
# on these configurations are the ones the cube split used, with the stated sizes, and the
# representatives exist.py fixed lie one per orbit.
Configurations := function(points, M0, k)
  # all matchings of exactly k pairs on `points` avoiding the pairs in M0, as sets of sets
  local rec_, out;
  out := [];
  rec_ := function(avail, chosen)
    local a, b, i, e, rest;
    if Length(chosen) = k then Add(out, Set(chosen)); return; fi;
    if Length(avail) < 2*(k - Length(chosen)) then return; fi;
    a := avail[1];
    # either a is left out (only if leave capacity remains) or a is matched to some b
    if Length(avail) - 1 >= 2*(k - Length(chosen)) then
      rec_(avail{[2..Length(avail)]}, chosen);
    fi;
    for i in [2..Length(avail)] do
      b := avail[i]; e := Set([a, b]);
      if e in M0 then continue; fi;
      rest := Filtered(avail, x -> x <> a and x <> b);
      rec_(rest, Concatenation(chosen, [e]));
    od;
  end;
  rec_(points, []);
  return Set(out);
end;

Check := function(name, npoints, r0, r1, reps)
  local points, M0, G1, confs, orbs, sizes, r, o, i, hit;
  points := [3..npoints-1];
  M0 := Set(List([2..r0], i -> Set([2*i-1, 2*i])));
  G1 := Stabilizer(SymmetricGroup(points), M0, OnSetsSets);
  Print(name, ": points ", points, " M0 ", M0, "\n");
  Print("  |G1| = ", Size(G1), "\n");
  confs := Configurations(points, M0, r1 - 1);
  Print("  row-1 configurations: ", Length(confs), "\n");
  orbs := OrbitsDomain(G1, confs, OnSetsSets);
  sizes := List(orbs, Length);
  Print("  orbits: ", Length(orbs), " sizes ", sizes, " (sum ", Sum(sizes), ")\n");
  hit := [];
  for i in [1..Length(reps)] do
    r := Set(List(reps[i], Set));
    o := First([1..Length(orbs)], j -> r in orbs[j]);
    if o = fail then Print("  rep ", i-1, " is NOT a configuration in the list\n");
    else
      Add(hit, o);
      Print("  rep ", i-1, " -> orbit ", o, " of size ", Length(orbs[o]), ", stabiliser order ", Size(Stabilizer(G1, r, OnSetsSets)), "\n");
    fi;
  od;
  Print("  representatives hit ", Length(Set(hit)), " distinct orbits of ", Length(orbs), "\n");
  if Length(Set(hit)) = Length(orbs) and Length(hit) = Length(orbs) then
    Print("  VERDICT ", name, ": the representatives are a transversal of the G1-orbits (every configuration lies in the orbit of exactly one representative)\n");
  else
    Print("  VERDICT ", name, ": FAILED, the representatives are not a transversal\n");
  fi;
end;

# (15,32): point 0 has 7 blocks (r0 = 7, no leave); point 1 has 7 blocks: {0,1,2} + 6 pairs of {3..14}
Check("(15,32)", 15, 7, 7,
  [ [[3,5],[4,6],[7,9],[8,10],[11,13],[12,14]],
    [[3,5],[4,6],[7,9],[8,11],[10,13],[12,14]],
    [[3,5],[4,7],[6,8],[9,11],[10,13],[12,14]],
    [[3,5],[4,7],[6,9],[8,11],[10,13],[12,14]] ]);

# (14,27): point 0 has 6 blocks (r0 = 6) and one leave point, 13; point 1 has 6 blocks:
# {0,1,2} + 5 pairs among {3..13}, one point left out
Check("(14,27)", 14, 6, 6,
  [ [[3,5],[4,6],[7,9],[8,10],[11,13]], [[3,5],[4,6],[7,9],[8,11],[10,12]],
    [[3,5],[4,6],[7,9],[8,11],[10,13]], [[3,5],[4,7],[6,8],[9,11],[10,13]],
    [[3,5],[4,7],[6,9],[8,10],[11,13]], [[3,5],[4,7],[6,9],[8,11],[10,12]],
    [[3,5],[4,7],[6,9],[8,11],[10,13]] ]);
