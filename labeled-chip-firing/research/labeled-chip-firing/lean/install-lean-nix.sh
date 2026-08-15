#!/usr/bin/env bash
# Install Lean 4 github-free, via Nix — the route that works when github.com
# egress is policy-blocked (elan and release.lean-lang.org both 302 to GitHub
# releases and 403). Everything here is pulled from the NixOS CDN
# (releases.nixos.org) and the binary cache (cache.nixos.org) — zero GitHub.
# Captured as the reusable installer the P5 ledger's open edge (c) asked for.
#
# Idempotent: if `lean` is already reachable it exits early.
set -euo pipefail

export PATH="$HOME/.elan/bin:$HOME/.nix-profile/bin:$PATH"
if command -v lean >/dev/null 2>&1; then
  echo "lean already present: $(lean --version)"; exit 0
fi

# 1. Single-user-as-root has no `nixbld` build-users group, and the Nix binary
#    defaults to `build-users-group = nixbld` — which aborts the install before our
#    config could land. So disable it BEFORE the installer runs: both in the config
#    it reads (/etc/nix/nix.conf) and via NIX_CONFIG in the environment.
mkdir -p /etc/nix
if ! grep -q "build-users-group" /etc/nix/nix.conf 2>/dev/null; then
  echo "build-users-group =" >> /etc/nix/nix.conf
fi
export NIX_CONFIG="build-users-group ="

# 2. Install Nix (single-user; this container runs as root, so no daemon).
if ! command -v nix-env >/dev/null 2>&1; then
  echo "Installing Nix (single-user, from releases.nixos.org) …"
  sh <(curl -L https://nixos.org/nix/install) --no-daemon --yes
  # shellcheck disable=SC1090
  . "$HOME/.nix-profile/etc/profile.d/nix.sh" 2>/dev/null || \
    . /root/.nix-profile/etc/profile.d/nix.sh 2>/dev/null || true
fi
export PATH="$HOME/.nix-profile/bin:$PATH"

# 3. Add the nixpkgs channel and install lean4 (prebuilt, from cache.nixos.org).
nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs || true
nix-channel --update
nix-env -iA nixpkgs.lean4

lean --version
echo "Lean ready. Add \$HOME/.nix-profile/bin to PATH."
