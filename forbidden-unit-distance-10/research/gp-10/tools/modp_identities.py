"""Every polynomial identity in the refutation certificates, re-checked modulo large primes without FLINT or sympy.

usage: python modp_identities.py RECORDS.jsonl OUT.json [--points 3]

The official checker and the blind second verifier both expand these identities in python-flint. This check shares no
code with FLINT, sympy or either verifier: it regenerates the system from the graph6 string (its own decoder), then
evaluates both sides of every identity at random points modulo p = 2^61 - 1 and p = 2^127 - 1, in Python integers.
An identity that holds over Q holds modulo p whenever no denominator vanishes mod p (checked; a vanishing denominator
is reported, never skipped). A false identity of degree d survives a random point with probability at most d/p
(Schwartz-Zippel), so --points 3 at each prime leaves one undetected with probability below 1e-200.

Checked: null (sum = 1); real (sum = f); null-dag and real-dag (every row's identity, then the last row = 1 or = f);
for SOS, f = c + sum w q^2 with c > 0 and every w > 0. A Sturm certificate's claim that f has no real root is not an
identity and is not re-checked here (both verifiers count the Sturm sequence; the blind one also asks sympy).
Built-in red controls: a coefficient changed, a cofactor term dropped, a row identity broken, an SOS weight changed.
"""
import sys, json, random, time, copy
from fractions import Fraction
from collections import Counter

REC, OUT = sys.argv[1:3]
PTS = int(sys.argv[sys.argv.index("--points") + 1]) if "--points" in sys.argv else 3
PRIMES = [(1 << 61) - 1, (1 << 127) - 1]
POLY = ("null", "real", "null-dag", "real-dag")


class Fail(Exception):
    pass


def decode_g6(s):
    n = ord(s[0]) - 63
    bits = []
    for ch in s[1:]:
        v = ord(ch) - 63
        bits += [(v >> (5 - i)) & 1 for i in range(6)]
    edges, k = set(), 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                edges.add((i, j))
            k += 1
    return n, edges


def check(rec, rng):
    """Raises Fail with a reason, or returns the number of identities checked (per point)."""
    c = rec["cert"]
    t = c["type"]
    n, E = decode_g6(rec["g6"])
    a, b = c["frame"]
    if (min(a, b), max(a, b)) not in E:
        raise Fail("frame is not an edge")
    names = [f"{z}_{i}" for i in range(n) if i not in (a, b) for z in ("x", "y")] + [f"t_{k}" for k in range(len(c["sat"]))]
    nv = len(names)
    identities = 0
    for p in PRIMES:
        cache = {}

        def r(s):
            if s not in cache:
                q = Fraction(s)
                if q.denominator % p == 0:
                    raise Fail(f"denominator of {s} vanishes mod p")
                cache[s] = q.numerator % p * pow(q.denominator, -1, p) % p
            return cache[s]

        for _ in range(PTS):
            pt = [rng.randrange(p) for _ in range(nv)]
            val = dict(zip(names, pt))

            def ev(poly):
                acc = 0
                for coef, ex in poly:
                    if len(ex) != nv:
                        raise Fail("exponent vector of the wrong length")
                    m = r(coef)
                    for v, e in zip(pt, ex):
                        if e:
                            m = m * pow(v, e, p) % p
                    acc += m
                return acc % p

            X = lambda i: 0 if i == a else (1 if i == b else val[f"x_{i}"])
            Y = lambda i: 0 if i in (a, b) else val[f"y_{i}"]
            d2 = lambda u, v: ((X(u) - X(v)) ** 2 + (Y(u) - Y(v)) ** 2) % p
            gens = {f"e:{u},{v}": (d2(u, v) - 1) % p for (u, v) in E if {u, v} != {a, b}}
            for k, (u, v) in enumerate(c["sat"]):
                if not u < v:
                    raise Fail("saturation pair not stored u < v")
                gens[f"s:{u},{v}"] = (val[f"t_{k}"] * d2(u, v) - 1) % p
            f_val = ev(c["f"]) if t in ("real", "real-dag") else None
            target = 1 if t in ("null", "null-dag") else f_val

            def combo(cof, extra):
                acc = 0
                for key, poly in cof.items():
                    if key in gens:
                        src = gens[key]
                    elif key.startswith("aux:") and extra is not None and key[4:].isdigit() and int(key[4:]) < len(extra):
                        src = extra[int(key[4:])]
                    else:
                        raise Fail(f"unknown or forward source {key}")
                    acc += ev(poly) * src
                return acc % p

            if t in ("null", "real"):
                if combo(c["cofactors"], None) != target:
                    raise Fail("cofactor identity fails")
                identities += 1
            else:
                aux = []
                for k, row in enumerate(c["rows"]):
                    P = ev(row["poly"])
                    if combo(row["cofactors"], aux) != P:
                        raise Fail(f"row {k} identity fails")
                    aux.append(P)
                    identities += 1
                if aux[-1] != target:
                    raise Fail("last row is not the target")
            if "sos" in c:
                s = c["sos"]
                if not Fraction(s["c"]) > 0 or not all(Fraction(w) > 0 for w, _ in s["squares"]):
                    raise Fail("SOS constant or weight not positive")
                if (r(s["c"]) + sum(r(w) * ev(q) ** 2 for w, q in s["squares"])) % p != f_val:
                    raise Fail("SOS identity fails")
                identities += 1
    return identities


T0 = time.time()
rng = random.Random(20260925)
counts, fails, idents, firsts = Counter(), [], 0, {}
with open(REC) as fh:
    for line in fh:
        rec = json.loads(line)
        t = rec["cert"]["type"]
        if t not in POLY:
            counts["not polynomial: " + t] += 1
            continue
        try:
            idents += check(rec, rng)
            counts[t + " ok"] += 1
            firsts.setdefault(t, rec)
            if "sos" in rec["cert"]:
                firsts.setdefault(t + "+sos", rec)
        except Fail as e:
            fails.append((rec["g6"], t, str(e)))
            counts[t + " FAIL"] += 1
            print("FAIL", rec["g6"], t, e, flush=True)

# red controls: each mutation of a real, passing record must FAIL here
red = []
def mutate(name, t, fn):
    if t not in firsts:
        return
    m = copy.deepcopy(firsts[t])
    before = json.dumps(m, sort_keys=True)
    fn(m["cert"])
    assert json.dumps(m, sort_keys=True) != before, name + " changed nothing"
    try:
        check(m, rng)
        red.append({"control": name, "red": False})
        print("GREEN?!", name, flush=True)
    except Fail as e:
        red.append({"control": name, "red": True, "reason": str(e)})
        print("RED  ", name, "--", e, flush=True)

def bump_first(poly):
    poly[0][0] = str(Fraction(poly[0][0]) + 1)

mutate("null: first cofactor's first coefficient + 1", "null", lambda c: bump_first(next(iter(c["cofactors"].values()))))
mutate("null: a cofactor term dropped", "null", lambda c: next(iter(c["cofactors"].values())).pop())
mutate("real: f's first coefficient + 1", "real", lambda c: bump_first(c["f"]))
mutate("null-dag: row 0 poly coefficient + 1", "null-dag", lambda c: bump_first(c["rows"][0]["poly"]))
mutate("null-dag: last row's cofactors emptied", "null-dag", lambda c: c["rows"][-1].__setitem__("cofactors", {}))
mutate("real-dag: an SOS weight doubled", "real-dag+sos",
       lambda c: c["sos"]["squares"][0].__setitem__(0, str(2 * Fraction(c["sos"]["squares"][0][0]))))
mutate("real: the SOS constant changed", "real+sos", lambda c: c["sos"].__setitem__("c", str(Fraction(c["sos"]["c"]) + 1)))
mutate("real-dag: a frame swapped for a non-edge", "real-dag", lambda c: c.__setitem__("frame", [c["frame"][0], c["frame"][0]]))

rep = {"primes": ["2^61-1", "2^127-1"], "points_per_prime": PTS, "seed": 20260925, "counts": dict(counts),
       "identities_checked_per_point": idents // (len(PRIMES) * PTS), "failures": fails, "red_controls": red,
       "all_red": all(x["red"] for x in red) and len(red) > 0, "seconds": round(time.time() - T0)}
rep["verdict"] = "MODP PASS" if not fails and rep["all_red"] else "MODP FAIL"
json.dump(rep, open(OUT, "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("verdict", "counts", "identities_checked_per_point", "seconds")}), flush=True)
