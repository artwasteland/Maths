\\ The stored generator need not be integral, irreducible, or minimal for
\\ the coordinates. Every change of generator also changes every coordinate.
default(nbthreads, 1);
default(realprecision, 250);
default(parisizemax, 512000000);
x = 'x; t = 't;
P = t; TH = 0.; R = List(); NF = nfinit(P);

value(a) = real(subst(lift(a), t, TH));
push(a) = { listput(R, Mod(lift(a), P)); return(#R); };
remap(a) = for(j = 1, #R, R[j] = Mod(subst(lift(R[j]), t, a), P));

isolate(Q, root, bounds = []) = {
  my(den, lo, hi);
  forstep(bits = 160, 640, 80,
    den = 2^bits;
    \\ Straddle exact dyadic roots as well as irrational roots.
    lo = (floor(root * den) - 1) / den;
    hi = lo + 3 / den;
    if(#bounds && (lo <= bounds[1] || hi >= bounds[2]), next);
    if(subst(Q, t, lo) * subst(Q, t, hi) < 0,
      if(polsturm(Q, [lo, hi]) == 1, return([lo, hi]))
    )
  );
  error("field:root_interval");
};

selectbase(Q, lo, hi) = {
  my(factors = factor(Q), roots, iv);
  for(i = 1, matsize(factors)[1],
    roots = polrootsreal(factors[i, 1]);
    for(j = 1, #roots,
      if(roots[j] > lo && roots[j] < hi,
        iv = isolate(factors[i, 1], roots[j], [lo, hi]);
        if(iv[1] > lo && iv[2] < hi,
          P = factors[i, 1]; TH = roots[j];
          if(poldegree(P) > DEGREE_CAP, error("field:degree_cap"));
          print("GP_BASE_DEGREE ", poldegree(P));
          return()
        )
      )
    )
  );
  error("field:base_root");
};

selectroot(Q, mapping, oldroot) = {
  my(roots = polrootsreal(Q), idx = 0, err = 1e100, delta);
  for(j = 1, #roots,
    delta = abs(subst(lift(mapping), t, roots[j]) - oldroot);
    if(delta < err, err = delta; idx = j)
  );
  if(idx == 0 || err > 1e-100, error("field:embedding_reduction"));
  return(roots[idx]);
};

reducefield() = {
  my(red = polredbest(P, 1), oldroot = TH);
  P = red[1];
  TH = selectroot(P, red[2], oldroot);
  remap(lift(red[2]));
  NF = nfinit(P);
};

rootfield(a) = {
  my(v, roots, ext, oldroot, mapold, b);
  if(a == 0, return(Mod(0, P)));
  v = value(a);
  if(v <= 0, error("extension:far"));
  roots = nfroots(NF, x^2 - a);
  if(#roots,
    for(j = 1, #roots, if(value(roots[j]) > 0, return(Mod(lift(roots[j]), P))));
    error("field:no_positive_root")
  );
  oldroot = TH;
  ext = rnfequation(NF, x^2 - a, 1);
  P = subst(ext[1], x, t);
  if(poldegree(P) > DEGREE_CAP, error("field:degree_cap"));
  mapold = subst(lift(ext[2]), x, t);
  TH = sqrt(v) + ext[3] * oldroot;
  remap(mapold);
  b = Mod(t - ext[3] * mapold, P);
  listput(R, b);
  reducefield();
  b = R[#R]; listpop(R);
  print("GP_EXTENSION_DEGREE ", poldegree(P));
  return(b);
};

finish(ids) = {
  my(d = #ids, dim = poldegree(P), C, B, T, Q, degree, U, V);
  my(ok = 0, oldroot, red, iv);
  C = matrix(dim, d, i, j, polcoef(lift(R[ids[j]]), i - 1, t));
  \\ A primitive element for the coordinates can be smaller than the base
  \\ field. Prove each coordinate's expression by an exact matrix identity.
  for(trial = 1, 8,
    T = sum(j = 1, d, (j + trial - 1)^trial * R[ids[j]]);
    Q = minpoly(T); degree = poldegree(Q);
    B = matrix(dim, degree, i, j, polcoef(lift(T^(j - 1)), i - 1, t));
    U = matinverseimage(B, C);
    if(matsize(U) == [degree, d] && B * U == C, ok = 1; break)
  );
  if(!ok, error("field:coordinate_primitive"));
  oldroot = value(T);
  Q = subst(Q, variable(Q), t);
  red = polredbest(Q, 1); Q = red[1];
  TH = selectroot(Q, red[2], oldroot);
  V = vector(d, j, Mod(subst(sum(i = 1, degree, U[i,j] * t^(i-1)), t, lift(red[2])), Q));
  Q = Q * denominator(Q); Q = Q / content(Q);
  iv = isolate(Q, TH);
  print("GP_FIELD_POLY ", vector(degree + 1, i, polcoef(Q, i - 1, t)));
  print("GP_FIELD_INTERVAL ", iv);
  print("GP_FIELD_COORDS ", vector(d, j, vector(degree, i, polcoef(lift(V[j]), i - 1, t))));
  print("GP_FIELD_OK");
};
