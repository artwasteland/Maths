#!/usr/bin/env bash
# ============================================================================
# ⚠⚠⚠ DO NOT RUN AS-IS — FALSIFIED BY MEASUREMENT 2026-07-02 (see WALL.md) ⚠⚠⚠
# A disk-backed sweep measured 2.55 BILLION frontier states at level 161 of 240
# with the census still growing and the width-23 plateau still ahead: a 96-128 GB
# VM would OOM after a few hours (~level 165). The projected peak is 2*10^10-10^13
# states/level — single-digit TERABYTES of fast NVMe (disk-backed engine:
# count_frontier5_ext.cpp, crash-resumable) at best, supercomputer scale at worst.
# This script is preserved as the record of the corrected plan, not a recipe.
# ============================================================================
# Turnkey: compute the EXACT a(5) — the five-bell extent count — on a big-RAM box.
#
# This is the one remaining task for request 007. The validated frontier counter
# (count_frontier4.cpp) just needs more RAM than a normal session has (~64 GB; the
# graph's intrinsic cut width is 23). Spin up a temporary big-memory VM, copy the
# /oversight/oeis/permutohedron-hamiltonian-cycles/ directory onto it, and run this
# script from inside that directory.
#
# WHERE TO GET THE RAM (2026-06-04):
#   - Oracle Cloud Always-Free ARM (Ampere A1) tops out at 4 cores / 24 GB — NOT enough.
#   - Use the signup TRIAL CREDIT (~$300/30-day; verify current amount): launch an
#     Ampere A1 Flex (ARM) or VM.Standard.E-Flex (x86) with ~96-128 GB RAM and 8-16
#     cores. A few hours costs single-digit dollars. PROVISION 96-128 GB, not exactly
#     64 — the 64 GB figure is an estimate and could be exceeded; RAM is cheap, a
#     swap-thrashing run is not. Tear the VM down when done.
#
# OCI PROVISIONING GOTCHA (RAM is NOT the storage spec):
#   - RAM is set by the SHAPE, not the disk. Create instance -> "Image and shape" ->
#     CHANGE SHAPE -> pick a *Flexible* shape (name ends in ".Flex": A1.Flex for ARM,
#     E4.Flex/E5.Flex for x86). ONLY a Flex shape gives you a MEMORY (GB) slider. A
#     fixed shape locks RAM to the core count, which is why "you can't spec RAM."
#   - The storage you saw (~46-50 GB) is the BOOT VOLUME (the disk) — a separate
#     section; that's your "HDD," not your memory. Bump it to ~100 GB for swap headroom.
#   - If a Flex shape won't launch: trials often hit "out of host capacity" on A1 (ARM)
#     -> use E4/E5.Flex (x86) instead, try another Availability Domain/region, or
#     UPGRADE TO PAY-AS-YOU-GO (you keep spending the same credits; the service limits
#     and capacity open up). PAYG is usually the unlock.
#   - Example that works: VM.Standard.E5.Flex, 4 OCPU, 96 GB memory, 100 GB boot,
#     Ubuntu 22.04 image. SSH in, copy this folder over, run this script.
#
# Validated here 2026-06-04: compiles cleanly, reproduces a(3)=1 and a(4)=44.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"
# If run from /research/, hop to where the counter + data live:
SRC=../../oversight/oeis/permutohedron-hamiltonian-cycles
[ -f count_frontier4.cpp ] || cd "$SRC"
[ -f count_frontier4.cpp ] || { echo "ERROR: run this from the permutohedron-hamiltonian-cycles/ dir (with count_frontier4.cpp + bs5_bfs.dat)"; exit 1; }

echo "### 1/4  toolchain ###"
command -v g++  >/dev/null || { sudo apt-get update -y && sudo apt-get install -y g++ git time; }
command -v git  >/dev/null || sudo apt-get install -y git

echo "### 2/4  TdZdd (header-only) ###"
[ -d /tmp/TdZdd/include ] || git clone --depth 1 https://github.com/kunisura/TdZdd /tmp/TdZdd

echo "### 3/4  compile ###"
g++ -O3 -march=native -I/tmp/TdZdd/include -o /tmp/cf4 count_frontier4.cpp
echo "compiled."

echo "### 3.5  sanity: n=4 must print 44 ###"
got=$(/tmp/cf4 bs4.dat 2>/dev/null | grep -oE 'cycles = [0-9]+' | grep -oE '[0-9]+')
echo "  n=4 -> $got  (expected 44)"
[ "$got" = "44" ] || { echo "ABORT: n=4 sanity failed — do not trust n=5."; exit 1; }

echo "### 4/4  THE RUN: exact a(5) on bs5_bfs.dat (needs ~64 GB; tens of minutes) ###"
echo "  watching peak memory; if it nears your RAM ceiling, kill it and use a bigger box."
if command -v /usr/bin/time >/dev/null; then
  /usr/bin/time -v /tmp/cf4 bs5_bfs.dat 2>&1 | tee a5-exact.out
else
  /tmp/cf4 bs5_bfs.dat | tee a5-exact.out
fi
echo
echo "============================================================"
echo "DONE. The line 'UNDIRECTED Hamiltonian cycles = N' above is a(5)."
echo "Next: put N as a(5) in b-file.txt and draft.txt (%S line -> 0,0,1,44,N),"
echo "drop the 'open'/estimate caveats, and it's a 5-term OEIS submission."
echo "============================================================"
