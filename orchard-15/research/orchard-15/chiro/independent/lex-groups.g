# lex-groups.g: compare exist.py's per-cube lex-leader group (dumped by the coordinator from
# exist.py's own data) with GAP's independent stabiliser of the representative in G1.
Read("independent/cube-groups.g");
CheckGroups := function(name, npoints, r0, reps)
  local points, M0, G1, i, r, S, E, D, ok;
  # the dump maps label i to GAP point i+1 (GAP points are positive), so shift every label
  points := [4..npoints];
  M0 := Set(List([2..r0], i -> Set([2*i, 2*i+1])));
  G1 := Stabilizer(SymmetricGroup(points), M0, OnSetsSets);
  ok := true;
  for i in [1..Length(reps)] do
    r := Set(List(reps[i], e -> Set(e + 1)));
    S := Stabilizer(G1, r, OnSetsSets);
    D := cubegroups.(Concatenation(name, ".", String(i-1)));
    E := Set(Elements(S));
    Print(name, " cube ", i-1, ": GAP stabiliser order ", Size(S), ", exist.py group size ", Length(D), ", identical as sets of permutations: ", Set(D) = E, "\n");
    if Set(D) <> E then ok := false; fi;
  od;
  if ok then Print("VERDICT ", name, ": every cube's lex-leader group IS the orbit stabiliser, element for element\n");
  else Print("VERDICT ", name, ": MISMATCH\n"); fi;
end;
CheckGroups("15-32", 15, 7,
  [ [[3,5],[4,6],[7,9],[8,10],[11,13],[12,14]], [[3,5],[4,6],[7,9],[8,11],[10,13],[12,14]],
    [[3,5],[4,7],[6,8],[9,11],[10,13],[12,14]], [[3,5],[4,7],[6,9],[8,11],[10,13],[12,14]] ]);
CheckGroups("14-27", 14, 6,
  [ [[3,5],[4,6],[7,9],[8,10],[11,13]], [[3,5],[4,6],[7,9],[8,11],[10,12]],
    [[3,5],[4,6],[7,9],[8,11],[10,13]], [[3,5],[4,7],[6,8],[9,11],[10,13]],
    [[3,5],[4,7],[6,9],[8,10],[11,13]], [[3,5],[4,7],[6,9],[8,11],[10,12]],
    [[3,5],[4,7],[6,9],[8,11],[10,13]] ]);
