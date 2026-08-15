#!/usr/bin/env bash
# Typecheck the labeled-chip-firing kernel enumeration and print the axiom
# footprint of every load-bearing theorem.
# Exit 0 with no error lines = QED (the kernel accepted the proofs).
set -euo pipefail
# Both toolchain routes: elan (~/.elan) when github egress is open, Nix
# (~/.nix-profile) when it is not. See install-lean.sh / install-lean-nix.sh.
export PATH="$HOME/.elan/bin:$HOME/.nix-profile/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"
command -v lean >/dev/null 2>&1 || {
  echo "Lean not found — run install-lean.sh (elan) or install-lean-nix.sh (github-free)." >&2; exit 127; }
echo "Lean: $(lean --version)"
echo "Typechecking ChipFiring.lean (all in the kernel; ~2–4 min) …"
lean "$HERE/ChipFiring.lean"
echo "✓ typechecks (no errors above)."
# Axiom footprints: each must read "does not depend on any axioms" and contain NO sorryAx.
tmp="$(mktemp --suffix=.lean)"
cat "$HERE/ChipFiring.lean" > "$tmp"
{
  printf '\n#print axioms even2_sorts\n'
  printf '#print axioms even4_sorts\n'
  printf '#print axioms even4_one_terminal\n'
  printf '#print axioms even6_sorts\n'
  printf '#print axioms odd3_count\n'
  printf '#print axioms odd5_count\n'
  printf '#print axioms odd3_branches\n'
  printf '#print axioms odd5_can_sort\n'
  printf '#print axioms boundary_safe\n'
  printf '#print axioms fuel_saturated_6\n'
} >> "$tmp"
echo "Axiom footprints (each must be 'does not depend on any axioms', no sorryAx):"
lean "$tmp" 2>&1 | grep -iE "depends on axioms|does not depend on any axioms" || true
rm -f "$tmp"
