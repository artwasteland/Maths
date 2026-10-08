"""Recognize reflection subfields; only exact edge identities yield proposals.

Numerical relations are discovery data. The ordinary frozen E-exact checker
still verifies the polynomial, common real interval, edges and injectivity.
"""
from common import *
import ast
import math
from decimal import Decimal, localcontext, ROUND_FLOOR
from fractions import Fraction
from flint import fmpq as Q, fmpq_poly as P
from exact import graph6
from late_stage import Budget, isolated, worker_main


def search(code, seconds, directory, evidence=None, work=None):
    return isolated(__file__, code, seconds, directory, evidence=evidence,
                    work=str(work) if work is not None else None)


def compose(a, b, modulus=None):
    value = P([])
    for c in reversed(list(a)):
        value = value * b + c
        if modulus is not None:
            value %= modulus
    return value


def primitive(p):
    values = list(map(int, p.numer()))
    divisor = math.gcd(*values)
    if values[-1] < 0:
        divisor = -divisor
    return P([v // divisor for v in values])


def inverse(p, modulus):
    g, a, _ = p.xgcd(modulus)
    if g != 1:
        raise ValueError("nonprimitive_extension")
    return a % modulus


def numerical_seed(request, budget):
    code = request["g6"]
    evidence = request.get("evidence") or {}
    points = evidence.get("points") or evidence.get("coords")
    frame = evidence.get("frame") or list(graph6(code)[1][0])
    if request.get("work"):
        work = Path(request["work"])
        key = hashlib.sha256(code.encode()).hexdigest()[:16]
        for name in ("refinement.json", "numeric.json"):
            path = work / "numeric" / key / name
            if path.exists():
                value = json.loads(path.read_text())
                candidate = value.get("points") or value.get("coords")
                if candidate:
                    points = candidate
                    frame = value.get("frame") or frame
                    budget.detail["numerical_source"] = str(path)
                    break
        if points is None:
            for path in sorted(work.glob("*-cases/" + key + "/**/*coordinate-proposal.json")):
                value = json.loads(path.read_text())
                if value.get("g6") != code:
                    continue
                cert = value["cert"]
                precision = max(160, min(16000, max(len(q) for xy in cert["coords"] for axis in xy for q in axis)+100))
                poly = "Polrev(" + str(cert["field"]["minpoly"]) + ")"
                lo, hi = cert["field"]["interval"]
                coords = ["Polrev([" + ",".join(c) + "])" for xy in cert["coords"] for c in xy]
                # Long rational coordinates can lose thousands of digits when evaluated.
                source = (f"default(nbthreads,1);default(realprecision,{precision});default(parisizemax,600000000);\np=" + poly + ";\n"
                          "r=polrootsreal(p);t=0;found=0;for(i=1,#r,if(r[i]>(" + lo + ")&&r[i]<(" + hi + "),t=r[i];found++));\n"
                          'print("ROOT_COUNT ",found);\n'
                          "C=[" + ",".join(coords) + "];for(i=1,#C,print(subst(C[i],x,t)));quit;\n")
                lines = budget.tool(source, ".gp", ["gp", "-fq", "-s", "64000000"]).splitlines()
                if not lines or lines.pop(0) != "ROOT_COUNT 1":
                    budget.detail.setdefault("proposal_attempts", []).append({"source": str(path), "reason": "proposal_root_interval"})
                    continue
                if len(lines) == 2 * len(cert["coords"]):
                    points = [lines[i:i+2] for i in range(0, len(lines), 2)]
                    budget.detail["numerical_source"] = str(path)
                    break
    if points is None:
        raise ValueError("no_separated_seed")
    return points, frame


def refine(code, points, frame, digits, budget):
    import mpmath as mp
    import numpy as np
    from scipy.linalg import qr
    n, edges = graph6(code)
    free = [v for v in range(n) if v not in frame]
    index = {v: 2*i for i, v in enumerate(free)}
    mp.mp.dps = 80
    # The first Newton pass needs 80 digits, including for long saved proposals.
    # Round before mpmath's integer parser without weakening Python's digit limit.
    with localcontext() as context:
        context.prec = 80
        p = [[mp.mpf(str(+Decimal(str(q)))) for q in xy] for xy in points]
    a, b = frame
    dx, dy = [p[b][j] - p[a][j] for j in (0, 1)]
    norm = mp.sqrt(dx*dx + dy*dy)
    p = [[((xy[0]-p[a][0])*dx+(xy[1]-p[a][1])*dy)/norm,
          ((xy[1]-p[a][1])*dx-(xy[0]-p[a][0])*dy)/norm] for xy in p]
    p[a] = [mp.mpf(0), mp.mpf(0)]
    p[b] = [mp.mpf(1), mp.mpf(0)]
    gap = min(mp.sqrt(sum((p[u][j]-p[v][j])**2 for j in (0, 1))) for v in range(n) for u in range(v))
    if gap < mp.mpf("1e-6"):
        raise ValueError("no_separated_seed")
    edges = [e for e in edges if set(e) != set(frame)]

    def equations():
        f = mp.matrix(len(edges), 1)
        jac = mp.matrix(len(edges), 2*len(free))
        for k, (u, v) in enumerate(edges):
            d = [p[u][j] - p[v][j] for j in (0, 1)]
            f[k] = sum(t*t for t in d) - 1
            for j in (0, 1):
                if u in index:
                    jac[k, index[u]+j] = 2*d[j]
                if v in index:
                    jac[k, index[v]+j] = -2*d[j]
        return f, jac

    _, jac = equations()
    matrix = np.array(jac.tolist(), dtype=float)
    _, r, pivots = qr(matrix.T, pivoting=True)
    rank = sum(abs(r[i, i]) > 1e-9 for i in range(min(r.shape)))
    if rank != 2*len(free):
        raise ValueError("numeric_jacobian_not_isolated")
    selected = list(map(int, pivots[:rank]))
    precision = 80
    while True:
        budget.remaining()
        mp.mp.dps = precision
        for _ in range(8):
            f, jac = equations()
            error = max(map(abs, f))
            if error < mp.mpf(10)**(-precision+20):
                break
            delta = mp.lu_solve(mp.matrix([[jac[k, j] for j in range(rank)] for k in selected]),
                                mp.matrix([f[k] for k in selected]))
            for v in free:
                for j in (0, 1):
                    p[v][j] -= delta[index[v]+j]
        if error >= mp.mpf(10)**(-precision+20):
            raise ValueError("refinement_stalled")
        if precision == digits:
            break
        precision = min(digits, 2*precision-30)
    gap = min(mp.sqrt(sum((p[u][j]-p[v][j])**2 for j in (0, 1))) for v in range(n) for u in range(v))
    if gap < mp.mpf("1e-6"):
        raise ValueError("refinement_collision")
    budget.detail.update(refined_error=mp.nstr(error, 8), refined_gap=mp.nstr(gap, 20), precision_digits=digits)
    result = [[mp.nstr(q, digits) for q in xy] for xy in p]
    write_json(budget.directory / "refined.json", dict(g6=code, frame=frame, points=result, precision_digits=digits))
    return result


def recognize(points, budget, combinations=False):
    # Overspecified algdep polynomials often contain rational extra factors.
    # Height and residual only rank proposals; exact identities are decisive.
    values = [v for xy in points for v in xy]
    source = "default(nbthreads,1);default(realprecision,6000);default(parisizemax,600000000);\n"
    source += "V=[" + ",".join(values) + "];\n"
    expressions = [f"V[{j+1}]" for j in range(0, len(values), 2)]
    if combinations:
        expressions = [f"V[{j+2}]" for j in range(0, len(values), 2)]
        expressions += [f"V[{j+1}]+{k}*V[{j+2}]" for k in (1, 2) for j in range(0, len(values), 2)]
    source += "U=[" + ",".join(expressions) + "];\n"
    source += "for(j=1,#U,for(k=1,5,d=[4,8,12,20,28][k];p=algdep(U[j],d);"
    source += "if(vecmax(abs(Vec(p)))<10^80,F=factor(p)[,1];for(l=1,#F,q=F[l];"
    source += "if(poldegree(q)>1&&abs(subst(q,x,U[j]))<10^-500,print(\"CAND \",j,\" \",Vecrev(q)))))));quit;\n"
    lines = budget.tool(source, ".gp", ["gp", "-fq", "-s", "64000000"]).splitlines()
    candidates = {}
    for line in lines:
        if line.startswith("CAND "):
            j, raw = line[5:].split(" ", 1)
            f = tuple(ast.literal_eval(raw))
            candidates[(int(j)-1, f)] = (len(f), max(abs(q).bit_length() for q in f))
    ranked = sorted(candidates, key=lambda item: (candidates[item], item[0]))
    budget.detail.setdefault("primitive_candidates", []).extend(dict(expression=expressions[j], degree=len(f)-1,
                                                    height_bits=candidates[(j, f)][1]) for j, f in ranked)
    budget.save()
    return ranked, source.split("for(j=")[0], expressions


def field_record(code, points, j, f, mode, relations, primitive_value=None):
    f = P(list(f))
    t = P([0, 1])
    if mode == "direct":
        p, x, scale = f, t, P([1])
    else:
        w = P([1, 0, -1]) if mode == "circle" else t*t/3
        even = P([f[k] for k in range(0, f.degree()+1, 2)])
        odd = P([f[k] for k in range(1, f.degree()+1, 2)])
        e, o = compose(even, w), compose(odd, w)
        p = primitive(e*e-w*o*o)
        x = -e*inverse(o, p) % p
        scale = t if mode == "circle" else t*inverse(x, p) % p
        if compose(f, x, p) or (x*x-w) % p:
            raise ValueError("extension_identity")
    coords = []
    for k, relation in enumerate(relations):
        if not relation[-1]:
            raise ValueError("dependent_recognition_basis")
        q = compose(P([Q(-c)/Q(relation[-1]) for c in relation[:-1]]), x, p)
        if k % 2:
            q = q*scale % p
        coords.append(q)
    n, edges = graph6(code)
    for a, b in edges:
        if (sum(((coords[2*a+k]-coords[2*b+k])**2 for k in (0, 1)), P([]))-1) % p:
            raise ValueError("recognized_edge_identity")
    for a in range(n):
        for b in range(a):
            if not sum(((coords[2*a+k]-coords[2*b+k])**2 for k in (0, 1)), P([])) % p:
                raise ValueError("recognized_collision")
    with localcontext() as context:
        context.prec = 160
        value = Decimal(primitive_value) if primitive_value is not None else Decimal(points[j//2][j%2])
        if mode == "circle":
            value = Decimal(points[j//2][1])
        elif mode == "sqrt3":
            value *= Decimal(3).sqrt()
        denominator = 10**100
        low = int((value*denominator).to_integral_value(rounding=ROUND_FLOOR))
    lo, hi = Q(low, denominator), Q(low+1, denominator)
    if p(lo)*p(hi) >= 0:
        raise ValueError("interval_sign_change")
    # A Sturm variation difference certifies that the proposed interval isolates.
    sequence = [p, p.derivative()]
    while sequence[-1]:
        remainder = -(sequence[-2] % sequence[-1])
        if not remainder:
            break
        sequence.append(remainder)
    def variations(value):
        signs = [1 if q(value) > 0 else -1 for q in sequence if q(value)]
        return sum(a != b for a, b in zip(signs, signs[1:]))
    if variations(lo)-variations(hi) != 1:
        raise ValueError("interval_not_isolating")
    return {"type": "exact", "field": {"minpoly": list(map(int, primitive(p))), "interval": [str(lo), str(hi)]},
            "coords": [[[str(coords[2*v+k][i]) for i in range(p.degree())] for k in (0, 1)] for v in range(n)]}


def worker(request):
    code = request["g6"]
    detail = {"method": "subfield_exact", "attempts": []}
    budget = Budget(request["seconds"]-.2, request["directory"], detail)
    budget.save()
    points, frame = numerical_seed(request, budget)
    detail["frame"] = frame
    budget.save()
    points = refine(code, points, frame, 6040, budget)
    for combinations in (False, True):
        candidates, prelude, expressions = recognize(points, budget, combinations)
        for candidate, f in candidates[:8]:
            j = 2*candidate if not combinations else 0
            modes = ["direct"] if combinations else ["sqrt3", "direct"]
            if not combinations and tuple(sorted((frame[0], j//2))) in graph6(code)[1] and abs(float(points[j//2][1])) > 1e-6:
                modes.insert(0, "circle")
            for mode in modes:
                cert = try_candidate(code, points, j, f, mode, expressions[candidate], prelude, budget)
                if cert:
                    return cert, detail
    return None, dict(detail, reason="no_recognized_exact_field")


def try_candidate(code, points, j, f, mode, expression, prelude, budget):
    detail = budget.detail
    begin = time.monotonic()
    scale = {"circle": f"V[{j+2}]", "sqrt3": "sqrt(3)", "direct": "1"}[mode]
    source = prelude + f"T={expression};S={scale};D={len(f)-1};W=vector(D,i,T^(i-1));print(\"VALUE \",T);\n"
    source += "for(j=1,#V,Z=if(j%2==0,V[j]/S,V[j]);L=lindep(concat(W,[Z]));print(\"REL \",L));quit;\n"
    attempt = {"expression": expression, "mode": mode, "degree": len(f)-1}
    detail["attempts"].append(attempt)
    budget.save()
    try:
        lines = budget.tool(source, ".gp", ["gp", "-fq", "-s", "64000000"]).splitlines()
        relations = [ast.literal_eval(line[4:].rstrip("~")) for line in lines if line.startswith("REL ")]
        if len(relations) != 2*len(points):
            raise ValueError("missing_coordinate_relations")
        value = next(line[6:] for line in lines if line.startswith("VALUE "))
        cert = field_record(code, points, j, f, mode, relations, value)
        if len(compact({"g6": code, "verdict": "embedded", "cert": cert}).encode())+1 > MAX_RECORD:
            raise ValueError("record_limit")
        attempt.update(result="exact", seconds=time.monotonic()-begin)
        detail.update(reason="exact_embedding", degree=len(cert["field"]["minpoly"])-1,
                      isolating_interval_verified=True)
        return cert
    except Exception as exc:
        attempt.update(reason=type(exc).__name__+":"+str(exc)[-250:], seconds=time.monotonic()-begin)
        budget.save()
    return None


if __name__ == "__main__":
    worker_main(worker, search, 180)
