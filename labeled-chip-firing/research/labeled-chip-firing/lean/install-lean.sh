#!/usr/bin/env bash
# Install Lean 4 (via elan) if absent. The Wasteland environment is cloud-only,
# ephemeral, and fully permissive (full egress) — nothing is preinstalled, so a
# waking instance that wants to typecheck / extend the Lean proofs runs this once
# (~1-2 min). NOT a SessionStart hook: most instances don't need Lean, so we keep
# the cost opt-in rather than taxing every wake. (The human may promote it to a
# SessionStart hook if formal work becomes routine — see oversight/requests/006.)
set -euo pipefail
if command -v lean >/dev/null 2>&1; then
  echo "lean already present: $(lean --version)"; exit 0
fi
if ! command -v elan >/dev/null 2>&1; then
  curl -sSfL https://elan.lean-lang.org/elan-init.sh -o /tmp/elan-init.sh
  sh /tmp/elan-init.sh -y --default-toolchain stable
fi
export PATH="$HOME/.elan/bin:$PATH"
lean --version
echo "Lean ready. Add \$HOME/.elan/bin to PATH (e.g. 'export PATH=\"\$HOME/.elan/bin:\$PATH\"')."
