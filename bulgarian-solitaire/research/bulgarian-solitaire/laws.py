#!/usr/bin/env python3
"""Probe candidate LAWS in the s-Bulgarian family, computed exactly."""
from s_explore import analyze, has_fixed_point

def T(k): return k*(k+1)//2

print("=== LAW 1: at n = s*T_k, is the attractor unique (num_recurrent==1)? worst-case settling maxTail? ===")
for s in [1,2,3,4]:
    print(f"\n s={s}:")
    for k in range(1, 8):
        n = s*T(k)
        if n > 60: break
        a = analyze(n, s)
        fp = has_fixed_point(n, s)
        print(f"  k={k} n={n:3d}: num_recurrent={a['num_recurrent']:2d}  maxTail={a['max_tail']:3d}  "
              f"numCycles={a['num_cycles']}  fixedpt={fp}  (k^2={k*k}, k^2-k={k*k-k})")

print("\n=== LAW 2: s=2, recurrent count at square n = m^2 vs central trinomial A002426 (1,1,3,7,19,51,141,393) ===")
A002426 = [1,1,3,7,19,51,141,393,1107]
for m in range(1, 8):
    n = m*m
    if n > 60: break
    a = analyze(n, 2)
    print(f"  m={m} n={n:3d}: num_recurrent={a['num_recurrent']:4d}   A002426({m})={A002426[m]}   match={a['num_recurrent']==A002426[m]}")

print("\n=== LAW 3: which n have a fixed point, per s (the s-staircase numbers) ===")
for s in [1,2,3,4]:
    ns = [n for n in range(1,51) if has_fixed_point(n,s)]
    print(f"  s={s}: {ns}")
