/-
  ROSA'S PARITY CONDITION — why some graphs can NEVER be gracefully labelled,
  checked by Lean's kernel alone.

  A graph with m edges is *graceful* if its vertices carry distinct labels drawn
  from {0,1,…,m} so that the m edge labels |f(u)−f(v)| are exactly {1,2,…,m},
  each difference once. Whether every tree is graceful is the Graceful Tree
  Conjecture (Ringel–Kotzig 1964), still open. The stratum `every-difference-once`
  lets you play with graceful labellings, and shows a family that *provably
  cannot* be graceful: the friendship / Dutch-windmill graph F_k (k triangles
  sharing one hub) is graceful iff k ≡ 0 or 1 (mod 4) — Bermond–Kotzig (1978).
  The census `research/graceful-census/` confirms the impossibility by EXHAUSTION:
  it counts 0 graceful labellings at k = 2 and k = 3. But a count, however far it
  runs, only ever settles finitely many k. This file proves the necessity half —
  for EVERY k, with no search — the same parity move that defeats Langford's
  problem (`research/langford/lean/`) and the mutilated chessboard.

  THE OBSTRUCTION (Rosa 1967), in one line:
    In a graph where every vertex has EVEN degree, an edge label |f(u)−f(v)| has
    the same parity as f(u)+f(v), so the SUM of all edge labels is congruent to
    Σ_v deg(v)·f(v) ≡ 0 (mod 2) — it is even. But a graceful labelling makes that
    sum 1+2+…+m = m(m+1)/2. So m(m+1)/2 must be even, i.e. m ≡ 0 or 3 (mod 4).

  Both Eulerian families in the census fall to this one law:
    • the cycle C_n (every degree 2): graceful ⇒ n ≡ 0 or 3 (mod 4)   `cycle_necessity`
    • the windmill F_k (hub degree 2k, rim degree 2), m = 3k edges:
        graceful ⇒ 3k ≡ 0 or 3 (mod 4) ⇔ k ≡ 0 or 1 (mod 4)          `windmill_necessity`
  The second is exactly Bermond–Kotzig's necessity — the stratum's headline.

  Self-contained: ZERO imports (no Mathlib, no Std). The only facts used are core
  `List`/`Nat` lemmas from Lean's prelude. The only trusted component is Lean's
  type checker. `#print axioms` on every theorem → [propext, Quot.sound]
  (`Quot.sound` enters only through `List.Perm`); no `sorry`, no `Classical.choice`,
  no `native_decide` — the kernel evaluates every `decide` itself.

  Verify:  lean research/graceful-census/lean/Graceful.lean   (no errors = QED)
-/

namespace Graceful

/-! ## 0. |x − y| on ℕ, and its parity -/

/-- The absolute difference of two naturals (truncated subtraction picks the branch). -/
def diff (x y : Nat) : Nat := if x ≤ y then y - x else x - y

/-- An edge label |x−y| has the same parity as x+y (the crux of Rosa's argument). -/
theorem diff_mod2 (x y : Nat) : diff x y % 2 = (x + y) % 2 := by
  unfold diff; split <;> omega

/-! ## 1. The triangular number 1+2+…+m, and when it is even -/

/-- `tri m = 1 + 2 + … + m`, by its recurrence — no closed form, no division. -/
def tri : Nat → Nat
  | 0     => 0
  | (m+1) => tri m + (m+1)

/-- The list `[1, 2, …, m]`, whose sum is `tri m`. -/
def upto : Nat → List Nat
  | 0     => []
  | (m+1) => upto m ++ [m+1]

theorem upto_sum (m : Nat) : (upto m).sum = tri m := by
  induction m with
  | zero => rfl
  | succ n ih => simp only [upto, tri, List.sum_append, List.sum_cons, List.sum_nil, ih]; omega

/-- `tri` grows by an even amount every four steps: `tri (m+4) = tri m + (4m+10)`. -/
theorem tri_add_four (m : Nat) : tri (m + 4) = tri m + (4 * m + 10) := by
  have h1 : tri (m+1) = tri m + (m+1) := rfl
  have h2 : tri (m+2) = tri (m+1) + (m+2) := rfl
  have h3 : tri (m+3) = tri (m+2) + (m+3) := rfl
  have h4 : tri (m+4) = tri (m+3) + (m+4) := rfl
  omega

/-- The parity of `tri` has period four: `tri (4q+r) ≡ tri r (mod 2)`. -/
theorem tri_period (q r : Nat) : tri (4 * q + r) % 2 = tri r % 2 := by
  induction q with
  | zero => simp
  | succ n ih =>
    have e : 4 * (n + 1) + r = (4 * n + r) + 4 := by omega
    rw [e, tri_add_four]
    omega

/-- **When 1+2+…+m is even.** Exactly when `m ≡ 0 or 3 (mod 4)`. -/
theorem tri_even_iff (m : Nat) : tri m % 2 = 0 ↔ (m % 4 = 0 ∨ m % 4 = 3) := by
  have key : tri m % 2 = tri (m % 4) % 2 := by
    have h := tri_period (m / 4) (m % 4)
    rwa [Nat.div_add_mod] at h
  rw [key]
  have h4 : m % 4 = 0 ∨ m % 4 = 1 ∨ m % 4 = 2 ∨ m % 4 = 3 := by omega
  rcases h4 with h | h | h | h <;> rw [h] <;> decide

/-! ## 2. Rosa's residue law — the arithmetic core shared by both families -/

/-- Permutation preserves a `List Nat` sum (built from the four `Perm` constructors;
    no `decide`, so no `Classical.choice`). -/
theorem perm_sum {l₁ l₂ : List Nat} (h : l₁.Perm l₂) : l₁.sum = l₂.sum := by
  induction h with
  | nil => rfl
  | cons x _ ih => simp only [List.sum_cons, ih]
  | swap x y l => simp only [List.sum_cons]; omega
  | trans _ _ ih₁ ih₂ => rw [ih₁, ih₂]

/-- **ROSA'S RESIDUE LAW.** If a list of edge labels is a permutation of `{1,…,m}`
    (as every graceful labelling makes it) AND its sum is even (as every
    even-degree graph forces), then `m ≡ 0 or 3 (mod 4)`. -/
theorem rosa_residue {edges : List Nat} {m : Nat}
    (hperm : edges.Perm (upto m)) (heven : edges.sum % 2 = 0) :
    m % 4 = 0 ∨ m % 4 = 3 := by
  have hs : edges.sum = tri m := by rw [perm_sum hperm, upto_sum]
  rw [hs] at heven
  exact (tri_even_iff m).mp heven

/-! ## 3. The windmill F_k (Bermond–Kotzig necessity) -/

/-- The three edge differences of one triangle `(a,b)` joined to the hub `h`. -/
def triEdges (h : Nat) (t : Nat × Nat) : List Nat := [diff h t.1, diff h t.2, diff t.1 t.2]

/-- All 3k edge differences of the windmill: hub `h`, triangles `tris` (each `(a,b)`). -/
def windmillEdges (h : Nat) (tris : List (Nat × Nat)) : List Nat := tris.flatMap (triEdges h)

/-- One triangle contributes an EVEN sum of edge labels: (h+a)+(h+b)+(a+b) = 2(h+a+b). -/
theorem triEdges_sum_even (h : Nat) (t : Nat × Nat) : (triEdges h t).sum % 2 = 0 := by
  have h1 := diff_mod2 h t.1
  have h2 := diff_mod2 h t.2
  have h3 := diff_mod2 t.1 t.2
  simp only [triEdges, List.sum_cons, List.sum_nil]
  omega

/-- **The windmill's total edge-label sum is even** (every vertex has even degree). -/
theorem windmillEdges_sum_even (h : Nat) (tris : List (Nat × Nat)) :
    (windmillEdges h tris).sum % 2 = 0 := by
  induction tris with
  | nil => rfl
  | cons t ts ih =>
    have hhead := triEdges_sum_even h t
    simp only [windmillEdges, List.flatMap_cons, List.sum_append] at ih ⊢
    omega

/-- The windmill has `3k` edges. -/
theorem windmillEdges_length (h : Nat) (tris : List (Nat × Nat)) :
    (windmillEdges h tris).length = 3 * tris.length := by
  induction tris with
  | nil => rfl
  | cons t ts ih => simp only [windmillEdges, List.flatMap_cons, List.length_append,
      List.length, triEdges] at *; omega

/-- **BERMOND–KOTZIG NECESSITY, MACHINE-CHECKED.** If the friendship graph `F_k`
    (`k = tris.length` triangles round a hub `h`) has a labelling whose `3k` edge
    differences realise each of `1,…,3k` exactly once — which every graceful
    labelling does — then `k ≡ 0 or 1 (mod 4)`. Hence `F_2`, `F_3`, `F_6`, … are
    never graceful, for all k, no enumeration. -/
theorem windmill_necessity (h : Nat) (tris : List (Nat × Nat))
    (hperm : (windmillEdges h tris).Perm (upto (3 * tris.length))) :
    tris.length % 4 = 0 ∨ tris.length % 4 = 1 := by
  have hr := rosa_residue hperm (windmillEdges_sum_even h tris)
  -- hr : (3 * tris.length) % 4 = 0 ∨ (3 * tris.length) % 4 = 3
  omega

/-! ## 4. The cycle C_n -/

/-- Edge differences along an open path of vertex labels `prev, x₀, x₁, …`
    (each `xᵢ` paired with its predecessor). -/
def pathEdges : Nat → List Nat → List Nat
  | _,    []      => []
  | prev, (x::xs) => diff prev x :: pathEdges x xs

/-- The last label on the path (or `prev` if the tail is empty). -/
def pathLast : Nat → List Nat → Nat
  | prev, []      => prev
  | _,    (x::xs) => pathLast x xs

/-- **Telescoping parity.** The open path's edge-label sum has parity `prev + last`. -/
theorem pathEdges_parity (prev : Nat) (l : List Nat) :
    (pathEdges prev l).sum % 2 = (prev + pathLast prev l) % 2 := by
  induction l generalizing prev with
  | nil => simp only [pathEdges, pathLast, List.sum_nil]; omega
  | cons x xs ih =>
    have hd := diff_mod2 prev x
    simp only [pathEdges, pathLast, List.sum_cons]
    have := ih x
    omega

/-- The `n` cyclic edge differences of a list of vertex labels `v :: vs`: the open
    path `v-vs₀-vs₁-…`, then the wrap-around edge from the last vertex back to `v`.
    (`v` is paired with `vs`, never with itself — one edge per vertex, `n` in all.) -/
def cycleEdges : List Nat → List Nat
  | []        => []
  | (v :: vs) => pathEdges v vs ++ [diff (pathLast v vs) v]

/-- **The cycle's total edge-label sum is even** (every vertex has degree two). -/
theorem cycleEdges_sum_even (v : Nat) (vs : List Nat) :
    (cycleEdges (v :: vs)).sum % 2 = 0 := by
  have hpath := pathEdges_parity v vs
  have hwrap := diff_mod2 (pathLast v vs) v
  simp only [cycleEdges, List.sum_append, List.sum_cons, List.sum_nil]
  omega

/-- The number of cyclic edges equals the number of vertices. -/
theorem cycleEdges_length (v : Nat) (vs : List Nat) :
    (cycleEdges (v :: vs)).length = (v :: vs).length := by
  have hp : (pathEdges v vs).length = vs.length := by
    induction vs generalizing v with
    | nil => rfl
    | cons x xs ih => simp only [pathEdges, List.length_cons]; rw [ih]
  simp only [cycleEdges, List.length_append, List.length_cons, List.length_nil, hp]

/-- **CYCLE NECESSITY, MACHINE-CHECKED.** If the cycle `C_n` on vertex labels
    `v :: vs` (`n = 1 + vs.length` vertices, so `n` edges) has a labelling whose
    `n` edge differences realise each of `1,…,n` exactly once, then
    `n ≡ 0 or 3 (mod 4)`. -/
theorem cycle_necessity (v : Nat) (vs : List Nat)
    (hperm : (cycleEdges (v :: vs)).Perm (upto (1 + vs.length))) :
    (1 + vs.length) % 4 = 0 ∨ (1 + vs.length) % 4 = 3 :=
  rosa_residue hperm (cycleEdges_sum_even v vs)

/-! ## 5. The certificates have teeth — hypotheses satisfiable, and impossibility real -/

-- A real graceful windmill at k = 1 (one triangle = C₃): hub 0, rim 1 and 3.
--   edges |0−1|=1, |0−3|=3, |1−3|=2 — the differences {1,2,3}, each once.
def W1 : List (Nat × Nat) := [(1, 3)]
theorem windmill1_perm : (windmillEdges 0 W1).Perm (upto (3 * W1.length)) := by
  show ([1, 3, 2] : List Nat).Perm [1, 2, 3]
  exact List.Perm.cons 1 (List.Perm.swap 2 3 [])
-- …and 1 ≡ 1 (mod 4), consistent with the theorem (non-vacuous).
theorem windmill1_ok : W1.length % 4 = 0 ∨ W1.length % 4 = 1 :=
  windmill_necessity 0 W1 windmill1_perm

-- The impossibility has teeth: NO windmill of k = 2 triangles can be graceful.
theorem windmill2_impossible :
    ¬ ∃ (h : Nat) (tris : List (Nat × Nat)),
        tris.length = 2 ∧ (windmillEdges h tris).Perm (upto (3 * tris.length)) := by
  rintro ⟨h, tris, hlen, hperm⟩
  have := windmill_necessity h tris hperm
  rw [hlen] at this
  omega

-- A real graceful cycle at n = 4 (C₄ is graceful, 4 ≡ 0 mod 4): cyclic order 0—4—1—2—0.
--   edges |0−4|=4, |4−1|=3, |1−2|=1, |2−0|=2 — the differences {1,2,3,4}, each once.
-- Built from the raw `Perm` constructors (`perm_middle` pulls each value to the
-- front, `swap` finishes) — `decide` on `List.Perm` would route through a Classical
-- instance, which we avoid to keep the footprint at [propext, Quot.sound].
theorem cycle4_perm : (cycleEdges [0, 4, 1, 2]).Perm (upto (1 + [4,1,2].length)) := by
  show ([4, 3, 1, 2] : List Nat).Perm [1, 2, 3, 4]
  refine (@List.perm_middle _ 1 [4, 3] [2]).trans ?_
  refine List.Perm.cons 1 ?_
  refine (@List.perm_middle _ 2 [4, 3] []).trans ?_
  refine List.Perm.cons 2 ?_
  exact List.Perm.swap 3 4 []
theorem cycle4_ok : (1 + [4,1,2].length) % 4 = 0 ∨ (1 + [4,1,2].length) % 4 = 3 :=
  cycle_necessity 0 [4, 1, 2] cycle4_perm

/-
  What is proved here, exactly:
  • `windmill_necessity`, `cycle_necessity`: for EVERY k (resp. n), the mere existence
    of a graceful labelling forces the mod-4 residue — no enumeration, no bound. The
    windmill statement is Bermond–Kotzig's necessity, the stratum's "provably cannot be
    graceful" headline; the cycle statement is the classic C_n condition (A333720).
  • `rosa_residue`: the shared arithmetic engine — Rosa's parity condition, once the
    even-degree structure has forced the edge-sum even.
  • `windmill1_ok`, `cycle4_ok`: real graceful members satisfy the hypotheses, so the
    theorems are not vacuous; `windmill2_impossible`: the k=2 windmill provably has none.
  • SUFFICIENCY (a graceful labelling exists FOR every allowed residue) is a
    construction, kept honestly apart — exhibited by the census, not claimed here.
  • Still zero imports; `#print axioms` on every theorem → [propext, Quot.sound].
-/

#print axioms windmill_necessity
#print axioms cycle_necessity
#print axioms rosa_residue
#print axioms windmill1_ok
#print axioms cycle4_ok
#print axioms windmill2_impossible

end Graceful
