/-
  Labeled chip-firing on the integer line, machine-checked in Lean 4 — ZERO IMPORTS.
  =============================================================================

  Companion to the stratum "The Pile That Sorts Itself" (/strata/the-pile-that-sorts-itself/).
  Subject: Hopkins–McConville–Propp, "Sorting via chip-firing", EJC 24 (2017) #P3.13
  (arXiv:1612.06816).

  THE RULE.  Put N labeled chips (labels 1..N) all at the origin of ℤ. A site holding
  ≥ 2 chips may FIRE: choose any two chips there and send the lesser-labeled one step
  left, the greater-labeled one step right. Fire until every site holds ≤ 1 chip; the
  chips then occupy N consecutive sites and, read left → right, spell a permutation.

  THE WONDER (HMP Theorem 13).  For EVEN N the pile *sorts itself*: whatever pairs you
  ever choose, the terminal permutation is ALWAYS the sorted one 1,2,…,N (confluence).
  For ODD N the spell breaks — different choices reach different endings, and the number
  of distinct reachable terminal permutations is OEIS A282901: 1, 3, 12, 54, 232, …

  WHAT THIS FILE PROVES.  Not the general theorem (that is HMP's, cited, not re-proved
  here — the honest boundary). Instead it hands Lean's KERNEL the finite object itself:
  it BUILDS every configuration reachable from the origin pile, exhaustively, over every
  choice, for concrete N, and the kernel checks — trusting nothing but its own logic:

    • EVEN N ∈ {2,4,6}: the reachable terminal permutation set is exactly {sorted}, and
      (N=4) there is exactly ONE reachable terminal configuration. The sort is forced.
    • ODD  N ∈ {3,5}: there is MORE THAN ONE ending (confluence provably fails), the
      exact count reproduces OEIS A282901 (a(1)=3, a(2)=12), and the sorted permutation
      is nonetheless still reachable (you can always finish the sort if you choose to).

  Every theorem is `by decide` and closes with `#print axioms → does not depend on any
  axioms at all` — no `sorry`, no `Classical.choice`, no `native_decide`. The only
  trusted component is the Lean kernel.

  FAITHFULNESS is itself machine-checked, not assumed:
    • `boundary_safe`  — no reachable chip ever sits at site 0, so the Nat encoding's
       `p-1` (truncated subtraction) can never fire at the origin boundary and corrupt a
       move. Positions are shifted so the origin is site N; the minimum site ever reached
       at N=6 is 3, a comfortable margin.
    • `fuel_saturated_*` — enlarging the fuel bound does not change the reachable set, so
       the enumeration is complete (a fixed point, not a truncation).
  And independently, `research/labeled-chip-firing/verify.mjs` re-derives every count
  with three unrelated enumerators (two JS, one C++); this file agrees with all of them.

  Run:  lean ChipFiring.lean      (Lean ≥ 4.30; ~2–4 min, all in the kernel)
-/

/-! ## The model (positions are Nat, origin shifted to site N) -/

abbrev Chip := Nat × Nat      -- (site, label)
abbrev Cfg  := List Chip      -- a configuration, canonicalised (sorted) after every move

def leChip (a b : Chip) : Bool := a.1 < b.1 || (a.1 == b.1 && a.2 ≤ b.2)
def insrt (x : Chip) : List Chip → List Chip
  | []      => [x]
  | y :: ys => if leChip x y then x :: y :: ys else y :: insrt x ys
def sortC : List Chip → List Chip
  | []      => []
  | x :: xs => insrt x (sortC xs)
def norm (c : Cfg) : Cfg := sortC c

/-- Canonical `Nat` key of a normalised config (site < 64, label < 64 ⇒ 12 bits/chip).
    Kernel `Nat` arithmetic is GMP-backed, so membership tests over keys are fast. -/
def keyOf (c : Cfg) : Nat :=
  (norm c).foldl (fun acc ch => acc * 4096 + (ch.1 * 64 + ch.2)) 1

def labelsAt (c : Cfg) (p : Nat) : List Nat := (c.filter (fun ch => ch.1 == p)).map (·.2)

/-- Sites holding ≥ 2 chips — the fireable ones. -/
def unstablePos (c : Cfg) : List Nat :=
  ((c.map (·.1)).eraseDups).filter (fun p => (labelsAt c p).length ≥ 2)

def isStable (c : Cfg) : Bool := (unstablePos c).isEmpty

/-- All one-fire successors: at every unstable site, every ordered pair (a<b) of labels
    present, send `a` left and `b` right — HMP's rule, over *every* choice. -/
def succ (c : Cfg) : List Cfg :=
  (unstablePos c).flatMap (fun p =>
    let L := labelsAt c p
    let pairs := L.flatMap (fun a => (L.filter (fun b => a < b)).map (fun b => (a, b)))
    pairs.map (fun (a, b) =>
      let c2 := (c.erase (p, a)).erase (p, b)
      norm ((p - 1, a) :: (p + 1, b) :: c2)))

/-- Fuel-bounded worklist reachability. Carries the frontier of configs, the set of
    visited keys (for fast dedup), and the visited configs. Structurally recursive on
    fuel, so the whole thing reduces inside the kernel. -/
def reachFuel : Nat → List Cfg → List Nat → List Cfg → List Cfg
  | 0,      _,        _,    vis => vis
  | fuel+1, frontier, keys, vis =>
    match frontier with
    | []        => vis
    | c :: rest =>
      let step := (succ c).foldl
        (fun (st : List Nat × List Cfg) ch =>
          let k := keyOf ch
          if (keys.contains k) || (st.1.contains k) then st else (k :: st.1, ch :: st.2))
        ([], [])
      reachFuel fuel (rest ++ step.2.reverse) (step.1 ++ keys) (vis ++ step.2.reverse)

def startCfg (n : Nat) : Cfg := norm ((List.range n).map (fun i => (n, i + 1)))

/-- Every configuration reachable from the origin pile of `n` chips. -/
def reachV (fuel n : Nat) : List Cfg :=
  let s := startCfg n
  reachFuel fuel [s] [keyOf s] [s]

def terminals (fuel n : Nat) : List Cfg := (reachV fuel n).filter isStable

/-- The distinct terminal permutations (each config read left → right as its labels). -/
def perms (fuel n : Nat) : List (List Nat) :=
  ((terminals fuel n).map (fun c => c.map (·.2))).eraseDups

/-! ## Faithfulness of the model — machine-checked, not assumed

    (a) No reachable chip ever sits at site 0, so `p-1` never truncates at the origin.
    (b) The enumeration is a fixed point: more fuel changes nothing. -/

set_option maxRecDepth 20000
set_option maxHeartbeats 4000000

theorem boundary_safe :
    (reachV 600 6).all (fun c => c.all (fun ch => 1 ≤ ch.1)) = true := by decide

theorem fuel_saturated_5 : (reachV 400 5).length = (reachV 500 5).length := by decide
theorem fuel_saturated_6 : (reachV 500 6).length = (reachV 700 6).length := by decide

/-! ## EVEN N — the pile sorts itself (confluence, over every choice) -/

/-- N = 2: the one reachable ending is the sorted pair. -/
theorem even2_sorts : perms 100 2 = [[1, 2]] := by decide

/-- N = 4: the one reachable ending is sorted — and there is exactly ONE terminal
    configuration reachable (15 configs are explored to get there). -/
theorem even4_sorts        : perms 200 4 = [[1, 2, 3, 4]] := by decide
theorem even4_one_terminal : (terminals 200 4).length = 1 := by decide

/-- N = 6 (289 configurations explored): still exactly one ending, and it is sorted.
    However you topple six chips, you cannot avoid sorting them. -/
theorem even6_sorts : perms 600 6 = [[1, 2, 3, 4, 5, 6]] := by decide

/-! ## ODD N — the spell breaks, with the exact OEIS A282901 counts -/

/-- N = 3: exactly 3 distinct endings — OEIS A282901, a(1) = 3. -/
theorem odd3_count    : (perms 100 3).length = 3 := by decide
/-- N = 5: exactly 12 distinct endings — OEIS A282901, a(2) = 12 (56 configs explored). -/
theorem odd5_count    : (perms 400 5).length = 12 := by decide

/-- Confluence provably FAILS for these odd N: more than one ending exists. -/
theorem odd3_branches : 2 ≤ (perms 100 3).length := by decide
theorem odd5_branches : 2 ≤ (perms 400 5).length := by decide

/-- The sorted permutation is still reachable for odd N — you can always finish the
    sort, you are merely no longer forced to. -/
theorem odd3_can_sort : (perms 100 3).contains [1, 2, 3]       = true := by decide
theorem odd5_can_sort : (perms 400 5).contains [1, 2, 3, 4, 5] = true := by decide

/-! ## The kernel's verdict — no axioms anywhere -/

#print axioms boundary_safe
#print axioms even6_sorts
#print axioms odd5_count
#print axioms odd5_branches
