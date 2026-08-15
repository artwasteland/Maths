#!/usr/bin/env bash
# Typecheck the graceful-labeling necessity theorems (Rosa's parity condition for
# the windmill and the cycle), and print the axiom footprint of each.
# Exit 0 with no error lines = QED (the kernel accepted the proofs).
set -euo pipefail
# Both toolchain routes: elan (~/.elan) when github egress is open, Nix
# (~/.nix-profile) when it is not. See install-lean.sh / install-lean-nix.sh.
export PATH="$HOME/.elan/bin:$HOME/.nix-profile/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"
command -v lean >/dev/null 2>&1 || {
  echo "Lean not found — run install-lean.sh (elan) or install-lean-nix.sh (github-free)." >&2; exit 127; }
echo "Lean: $(lean --version)"
echo "Typechecking Graceful.lean …"
lean "$HERE/Graceful.lean"
echo "✓ typechecks (no errors above)."
echo "Axiom footprints (each must be [propext, Quot.sound] or tighter, no sorryAx):"
lean "$HERE/Graceful.lean" 2>&1 | grep -i "depends on axioms\|does not depend" || true
