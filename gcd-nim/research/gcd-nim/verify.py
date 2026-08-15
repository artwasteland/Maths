#!/usr/bin/env python3
"""gcd-nim: the Python re-implementation. A second language, the same recursion.

Recomputes both games' Grundy sequences with its own mex loop and its own number
theory, and checks the load-bearing laws WITHOUT reference to the JS output, so
agreement is real evidence, not a copy. Run: python3 research/gcd-nim/verify.py

WHAT THIS PATH DOES AND DOES NOT COVER. It checks structural LAWS over n=0..6000.
It does not compare term-by-term against the JS values, and it does not read the
staged b-files: that binding is oversight/oeis/gcd-nim/verify-staged.mjs. It also
uses the same mex recursion as engine.mjs `grundy`, so what differs here is the
language and the implementation, not the algorithm.

DEPENDENCIES: none beyond the standard library. This file previously imported
sympy (primefactors, isprime, primepi). sympy is not present in a bare checkout,
so this "independent path" did not actually run from a fresh clone. The three
sympy calls are now a smallest-prime-factor sieve, below.
"""
from math import gcd

N = 6000

# --- number theory, standard library only -----------------------------------
# One smallest-prime-factor sieve to N answers all three questions the checks
# ask: is n prime (spf[n] == n), what is n's least prime factor, and what is that
# prime's index among the primes (2->1, 3->2, 5->3, ...).


def smallest_prime_factor_sieve(limit):
    spf = [0] * (limit + 1)
    for i in range(2, limit + 1):
        if spf[i] == 0:
            for j in range(i, limit + 1, i):
                if spf[j] == 0:
                    spf[j] = i
    return spf


SPF = smallest_prime_factor_sieve(N)
PRIME_INDEX = {}  # prime -> its 1-based index among the primes
for _p in range(2, N + 1):
    if SPF[_p] == _p:
        PRIME_INDEX[_p] = len(PRIME_INDEX) + 1


def isprime(n):
    return n >= 2 and SPF[n] == n


def lpf_index(n):
    if n < 2:
        return 0
    return PRIME_INDEX[SPF[n]]  # index of least prime factor (2->1, 3->2, ...)


def grundy(N, legal):
    g = [0] * (N + 1)
    for n in range(1, N + 1):
        seen = set()
        for d in range(1, n + 1):
            if legal(d, n):
                seen.add(g[n - d])
        m = 0
        while m in seen:
            m += 1
        g[n] = m
    return g

gc = grundy(N, lambda d, n: gcd(d, n) == 1)   # Coprime Nim
gk = grundy(N, lambda d, n: gcd(d, n) > 1)     # Common-factor Nim

fails = []
def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)

# POSITIVE CONTROLS on the replacement number theory, so the sieve that took
# sympy's place is itself checked rather than trusted.
check("stdlib sieve: primality matches trial division (n=2..2000)",
      all(isprime(n) == all(n % d for d in range(2, int(n ** 0.5) + 1)) for n in range(2, 2001)))
# A055396(1..24) transcribed from OEIS: a(n) = index of the smallest prime dividing n; a(1)=0.
A055396 = [0, 0, 1, 2, 1, 3, 1, 4, 1, 2, 1, 5, 1, 6, 1, 2, 1, 7, 1, 8, 1, 2, 1, 9, 1]
check("stdlib sieve: least-prime-factor index reproduces A055396 (n=1..24)",
      all(lpf_index(n) == A055396[n] for n in range(1, 25)))

# COPRIME: even->0 ; G(1)=1 ; odd>=3 -> lpf index
check("Coprime: G(even)=0 (n=2..N)", all(gc[n] == 0 for n in range(2, N + 1, 2)))
check("Coprime: G(1)=1", gc[1] == 1)
check("Coprime: G(odd n>=3) = index of least prime factor",
      all(gc[n] == lpf_index(n) for n in range(3, N + 1, 2)))

# COMMON: P-positions {0,1}; G(2k)=k; odd primes ->1; odd prime^2 ->2
check("Common: P-positions {0,1} only", gk[0] == 0 and gk[1] == 0 and all(gk[n] != 0 for n in range(2, N + 1)))
check("Common: G(2k)=k (n=2..N)", all(gk[n] == n // 2 for n in range(2, N + 1, 2)))
check("Common: G(odd prime)=1", all(gk[p] == 1 for p in range(3, N + 1, 2) if isprime(p)))
check("Common: G(odd prime^2)=2", all(gk[p * p] == 2 for p in range(3, int(N ** 0.5) + 1, 2) if isprime(p)))

print("  Coprime G(0..30):", ",".join(map(str, gc[:31])))
print("  Common  G(0..30):", ",".join(map(str, gk[:31])))
print(("ALL PASS" if not fails else "FAILURES: " + str(fails)), "—", "python", __import__("sys").version.split()[0])
raise SystemExit(1 if fails else 0)
