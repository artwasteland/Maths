"""Expanded Singular discovery and independent python-flint identity checks."""
from __future__ import annotations
import json
import itertools
import os
os.environ["SYMPY_GROUND_TYPES"] = "python"
import re
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from flint import fmpq, fmpq_mpoly_ctx
from graphs import SCRATCH, decode

class AlgebraError(ValueError):
    pass

def sparse(poly):
    return [[str(c), list(map(int,e))] for e, c in sorted(poly.to_dict().items()) if c]

def unsparse(ctx, value):
    if not isinstance(value, list):
        raise AlgebraError("polynomial: expected sparse list")
    terms = {}
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise AlgebraError("polynomial: invalid term")
        c, e = item
        if not isinstance(c, str) or not re.fullmatch(r"[+-]?\d+(?:/\d+)?", c):
            raise AlgebraError("polynomial: coefficient must be rational string")
        if not isinstance(e, list) or len(e) != ctx.nvars() or any(type(x) is not int or x < 0 for x in e):
            raise AlgebraError("polynomial: invalid exponent vector")
        key = tuple(e)
        if key in terms:
            raise AlgebraError("polynomial: duplicate monomial")
        if "/" in c and int(c.split("/")[1])<=0:
            raise AlgebraError("polynomial: denominator must be positive")
        terms[key] = fmpq(str(Fraction(c)))
    return ctx.from_dict(terms)

def expanded_parse(ctx, text):
    # Only the flat monomial grammar printed with Singular short=0 is allowed.
    text = text.replace(" ", "")
    if not text or any(c in text for c in "()[];\n"):
        raise AlgebraError("CAS polynomial is not pre-expanded")
    names = {n: i for i, n in enumerate(ctx.names())}
    result = ctx.constant(0)
    pieces = re.findall(r"[+-]?[^+-]+", text)
    if "".join(pieces) != text:
        raise AlgebraError("invalid CAS polynomial")
    for term in pieces:
        sign = -1 if term.startswith("-") else 1
        term = term.lstrip("+-")
        coeff, powers = fmpq(sign), [0] * ctx.nvars()
        for factor in term.split("*"):
            if re.fullmatch(r"\d+(?:/\d+)?", factor):
                coeff *= fmpq(factor)
            else:
                match = re.fullmatch(r"([a-z][a-z0-9]*)(?:\^(\d+))?", factor)
                if not match or match[1] not in names:
                    raise AlgebraError("invalid CAS monomial: " + factor)
                powers[names[match[1]]] += int(match[2] or "1")
        result += ctx.from_dict({tuple(powers): coeff})
    return result

def cycles4(n, edges):
    for a, c in itertools.combinations(range(n), 2):
        common = [b for b in range(n) if tuple(sorted((a,b))) in edges and tuple(sorted((c,b))) in edges]
        for b, d in itertools.combinations(common, 2):
            if (a, c) < (b, d):
                yield a, b, c, d

def choose_sat(n, edges, all_pairs=False):
    pairs = set()
    for a,b,c,d in cycles4(n,edges):
        pairs.update([tuple(sorted((a,c))), tuple(sorted((b,d)))])
    if all_pairs:
        pairs.update(itertools.combinations(range(n), 2))
    return sorted(pairs - set(edges))

def system(code, frame, sat, allow_nonedge=False):
    n, edges = decode(code)
    if (not isinstance(frame, list) or len(frame) != 2 or
        any(type(v) is not int or not 0 <= v < n for v in frame) or frame[0] == frame[1]):
        raise AlgebraError("frame: invalid pair")
    a, b = frame
    if tuple(sorted(frame)) not in edges and not allow_nonedge:
        raise AlgebraError("frame: not an edge")
    if not isinstance(sat, list):
        raise AlgebraError("sat: expected list")
    seen = set()
    for pair in sat:
        if (not isinstance(pair, list) or len(pair) != 2 or
            any(type(v) is not int or not 0 <= v < n for v in pair) or pair[0] >= pair[1]):
            raise AlgebraError("sat: invalid pair")
        if tuple(pair) in seen or tuple(pair) in edges:
            raise AlgebraError("sat: duplicate or adjacent pair")
        seen.add(tuple(pair))
    names = [name for i in range(n) if i not in frame for name in (f"x{i}",f"y{i}")]
    names += [f"t{k}" for k in range(len(sat))]
    # An empty ring is unnecessary: graphs with fewer than three vertices return unknown.
    if not names:
        raise AlgebraError("system: no variables")
    ctx = fmpq_mpoly_ctx.get(tuple(names), "degrevlex")
    variables = dict(zip(names, ctx.gens()))
    zero, one = ctx.constant(0), ctx.constant(1)
    coords = {i: (variables[f"x{i}"],variables[f"y{i}"]) for i in range(n) if i not in frame}
    coords[a], coords[b] = (zero,zero), (one,zero)
    def d2(u,v):
        return sum(((coords[u][j]-coords[v][j])**2 for j in (0,1)), zero)
    gens = {}
    for u,v in sorted(edges):
        if (u,v) != tuple(sorted(frame)):
            gens[f"e:{u},{v}"] = d2(u,v)-one
    for k,(u,v) in enumerate(sat):
        gens[f"s:{u},{v}"] = variables[f"t{k}"]*d2(u,v)-one
    return ctx, coords, gens

def add_scaled(out, source, factor):
    for k, v in source.items():
        p = out.get(k, factor.context().constant(0)) + factor*v
        if p:
            out[k] = p
        else:
            out.pop(k, None)

def rhombus_helpers(code, frame, sat, ctx, coords, gens):
    n, edges = decode(code)
    zero, one = ctx.constant(0), ctx.constant(1)
    inv = {tuple(pair): ctx.gen(2*(n-2)+k) for k,pair in enumerate(sat)}
    def eq(u,v):
        pair = tuple(sorted((u,v)))
        if pair == tuple(sorted(frame)):
            return {}
        return {f"e:{pair[0]},{pair[1]}": one}
    def inv_distance(pair):
        pair = tuple(sorted(pair))
        if pair in edges:
            return one, eq(*pair)
        return inv[pair], {f"s:{pair[0]},{pair[1]}": one}
    helpers = []
    for a,b,c,d in cycles4(n,edges):
        if any(tuple(sorted(p)) not in edges and tuple(sorted(p)) not in inv for p in [(a,c),(b,d)]):
            continue
        A = [coords[a][j]-coords[c][j] for j in (0,1)]
        B = [coords[b][j]-coords[d][j] for j in (0,1)]
        S = [coords[a][j]+coords[c][j]-coords[b][j]-coords[d][j] for j in (0,1)]
        aa = sum((v*v for v in A),zero); bb = sum((v*v for v in B),zero)
        ab = sum((A[j]*B[j] for j in (0,1)),zero)
        ta, ca = inv_distance((a,c)); tb, cb = inv_distance((b,d))
        sa, sb, cab = {}, {}, {}
        for pair,sa_w,sb_w,ab_w in [((a,b),1,-1,-1),((b,c),-1,-1,1),((c,d),-1,1,-1),((d,a),1,1,1)]:
            for out, weight in [(sa,sa_w),(sb,sb_w),(cab,ab_w)]:
                add_scaled(out,eq(*pair),ctx.constant(fmpq(weight,2)))
        for j in (0,1):
            if not S[j]:
                continue
            cert = {}
            add_scaled(cert, sa, ta*tb*(bb*A[j]-ab*B[j]))
            add_scaled(cert, sb, ta*tb*(aa*B[j]-ab*A[j]))
            add_scaled(cert, cab, ta*tb*ab*S[j])
            add_scaled(cert, ca, -S[j])
            add_scaled(cert, cb, -ta*aa*S[j])
            if sum((v*gens[k] for k,v in cert.items()),zero) != S[j]:
                raise AlgebraError("internal rhombus identity failed")
            helpers.append((S[j],cert))
    return helpers

def prepared_helpers(code, frame, sat, ctx, coords, gens, include_sat=True):
    n,edges = decode(code)
    rows = rhombus_helpers(code,frame,sat,ctx,coords,gens)
    zero,one = ctx.constant(0),ctx.constant(1)
    a,b = frame
    for v in range(n):
        av,bv = tuple(sorted((a,v))),tuple(sorted((b,v)))
        if av in edges and bv in edges:
            identity={f"e:{av[0]},{av[1]}":one/2,f"e:{bv[0]},{bv[1]}":-one/2}
            rows.append((coords[v][0]-one/2,identity))
    # RREF with proof coefficients. Pivot order is the polynomial variable order.
    pivot=0
    for i in range(ctx.nvars()):
        mon=tuple(1 if j==i else 0 for j in range(ctx.nvars()))
        found=next((j for j in range(pivot,len(rows)) if rows[j][0].to_dict().get(mon,0)),None)
        if found is None: continue
        rows[pivot],rows[found]=rows[found],rows[pivot]
        p,c=rows[pivot];scale=1/p.to_dict()[mon]
        p=p*scale;c={k:v*scale for k,v in c.items()};rows[pivot]=(p,c)
        for j,(q,d) in enumerate(rows):
            if j==pivot: continue
            factor=q.to_dict().get(mon,0)
            if factor:
                d=dict(d);add_scaled(d,c,ctx.constant(-factor));rows[j]=(q-factor*p,d)
        pivot+=1
    rows=[(p,c) for p,c in rows if p]
    prepared=list(rows)
    reduced_edges=[]
    for key,original in gens.items():
        if not include_sat and key.startswith("s:"): continue
        p=original;c={key:one}
        for h,hc in rows:
            q,p=divmod(p,h)
            if q: add_scaled(c,hc,-q)
        if key.startswith("s:"):
            for h,hc in reduced_edges:
                q,p=divmod(p,h)
                if q:add_scaled(c,hc,-q)
        elif p:
            reduced_edges.append((p,c))
        if p: prepared.append((p,c))
    unique={}
    for p,c in prepared:
        lead=p.leading_coefficient()
        p=p/lead;c={k:v/lead for k,v in c.items()}
        unique.setdefault(str(p),(p,c))
    prepared=list(unique.values())
    for p,c in prepared:
        if sum((v*gens[k] for k,v in c.items()),zero)!=p:
            raise AlgebraError("linear preprocessing identity failed")
    return prepared

def reduce_problem(ctx, helpers, target):
    linear=[(p,c) for p,c in helpers if max((sum(e) for e in p.to_dict()),default=0)<=1]
    linear.sort(key=lambda item: min((i for e,c in item[0].terms() for i,v in enumerate(e) if v),default=ctx.nvars()))
    reduced=[]
    for original,identity in helpers:
        if max((sum(e) for e in original.to_dict()),default=0)<=1:continue
        p=original;c=dict(identity)
        for h,hc in linear:
            q,p=divmod(p,h)
            if q:add_scaled(c,hc,-q)
        if p:reduced.append((p,c))
    remainder=target;difference={}
    for h,hc in linear:
        q,remainder=divmod(remainder,h)
        if q:add_scaled(difference,hc,q)
    return reduced,remainder,difference

def cas_run(script, seconds):
    SCRATCH.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cas-",dir=SCRATCH) as tmp:
        inp, out = Path(tmp)/"input.sing", Path(tmp)/"output.txt"
        inp.write_text(script)
        with out.open("w") as f:
            child = subprocess.Popen(["Singular","-q",str(inp)],stdout=f,stderr=subprocess.STDOUT,
                                     cwd=tmp, env={**os.environ,"OMP_NUM_THREADS":"1"})
            try:
                child.wait(timeout=max(0.001,seconds))
            except BaseException:
                child.kill(); child.wait()
                raise
        if out.stat().st_size > 16000000:
            raise AlgebraError("CAS output limit")
        output=out.read_text()
        if child.returncode:
            raise AlgebraError(f"CAS exit {child.returncode}: "+output[-300:])
        return output

def cas_prefix(ctx, polynomials, variable_order=None, ordering="dp"):
    text = [str(p).replace(" ","") for p in polynomials]
    if any("(" in p or ")" in p for p in text):
        raise AlgebraError("input not pre-expanded")
    names = list(ctx.names()) if variable_order is None else list(variable_order)
    if sorted(names) != sorted(ctx.names()) or ordering not in ("dp", "lp"):
        raise AlgebraError("invalid CAS variable order")
    return "ring r=0,("+",".join(names)+"),"+ordering+";\nshort=0;\noption(redSB);\nideal I="+",".join(text)+";\n"

def basis(ctx, polynomials, seconds, variable_order=None, ordering="dp", algorithm="std"):
    if algorithm not in ('std','slimgb'): raise AlgebraError('invalid basis algorithm')
    script = cas_prefix(ctx,polynomials,variable_order,ordering)+'ideal G='+algorithm+'(I);\nprint("GP10_BASIS_BEGIN");\nfor(int j=1;j<=size(G);j++){print(string(G[j]));}\nprint("GP10_BASIS_END");\nquit;\n'
    output = cas_run(script,seconds)
    lines = output.splitlines()
    if lines.count("GP10_BASIS_BEGIN") != 1 or lines.count("GP10_BASIS_END") != 1:
        raise AlgebraError("CAS: no exact basis marker")
    a,b = lines.index("GP10_BASIS_BEGIN"),lines.index("GP10_BASIS_END")
    if b <= a:
        raise AlgebraError("CAS: inverted markers")
    return [expanded_parse(ctx,line) for line in lines[a+1:b]]

def fglm_basis(ctx, gb, seconds, target=None, variable_order=None):
    target = target or ctx.names()[0]
    names = [v for v in ctx.names() if v != target] + [target]
    script = cas_prefix(ctx, gb, variable_order) + 'ideal G=I;attrib(G,"isSB",1);\n'
    script += 'if(dim(G)!=0){print("GP10_FGLM_SKIP");quit;}\n'
    script += 'ring s=0,('+','.join(names)+'),lp;short=0;ideal H=fglm(r,G);\n'
    script += 'print("GP10_BASIS_BEGIN");for(int j=1;j<=size(H);j++){print(string(H[j]));}print("GP10_BASIS_END");quit;\n'
    lines = cas_run(script, seconds).splitlines()
    if "GP10_FGLM_SKIP" in lines:
        return []
    if lines.count("GP10_BASIS_BEGIN") != 1 or lines.count("GP10_BASIS_END") != 1:
        raise AlgebraError("CAS: no exact FGLM markers")
    a,b = lines.index("GP10_BASIS_BEGIN"),lines.index("GP10_BASIS_END")
    return [expanded_parse(ctx,line) for line in lines[a+1:b]]

def lift(ctx, polynomials, target, seconds, variable_order=None, ordering="dp", algorithm="std"):
    script = cas_prefix(ctx,polynomials,variable_order,ordering)+"ideal J="+str(target).replace(" ","")+";\n"+'matrix U;matrix T=lift(I,J,U,"'+algorithm+'");\npoly V=0;\nfor(int k=1;k<=size(I);k++){V=V+I[k]*T[k,1];}\nif(V==J[1]){\n print("GP10_LIFT_EXACT");\n for(int j=1;j<=size(I);j++){print(string(T[j,1]));}\n print("GP10_LIFT_END");\n}else{print("GP10_LIFT_NO");}\nquit;\n'
    lines = cas_run(script,seconds).splitlines()
    if lines.count("GP10_LIFT_EXACT") != 1 or lines.count("GP10_LIFT_END") != 1:
        return None
    a,b = lines.index("GP10_LIFT_EXACT"),lines.index("GP10_LIFT_END")
    if b-a-1 != len(polynomials):
        raise AlgebraError("CAS: cofactor count")
    cofs = [expanded_parse(ctx,s) for s in lines[a+1:b]]
    if sum((p*q for p,q in zip(polynomials,cofs)),ctx.constant(0)) != target:
        raise AlgebraError("CAS: lift identity failed")
    return cofs

def homogeneous_lift(ctx, polynomials, target, seconds, padding=0, algorithm="std"):
    # h is a discovery-only homogenizer, set to 1 before any cofactor is emitted.
    hc=fmpq_mpoly_ctx.get(tuple(ctx.names())+("h",),"degrevlex")
    def homogenize(p,degree=None):
        terms=p.to_dict()
        degree=max((sum(e) for e in terms),default=0) if degree is None else degree
        return hc.from_dict({tuple(e)+(degree-sum(e),):c for e,c in terms.items()})
    hp=[homogenize(p) for p in polynomials]
    ht=homogenize(target,max((sum(e) for e in target.to_dict()),default=0)+padding)
    script=cas_prefix(hc,hp)+"ideal J="+str(ht).replace(" ","")+";\n"
    script+='degBound='+str(max((sum(e) for e in ht.to_dict()),default=0))+';\n'
    script+='matrix U;matrix T=lift(I,J,U,"'+algorithm+'");poly V=0;for(int k=1;k<=size(I);k++){V=V+I[k]*T[k,1];}\n'
    script+='if(V==J[1]){print("GP10_LIFT_EXACT");for(int j=1;j<=size(I);j++){print(string(subst(T[j,1],h,1)));}print("GP10_LIFT_END");}else{print("GP10_LIFT_NO");}quit;\n'
    lines=cas_run(script,seconds).splitlines()
    if lines.count("GP10_LIFT_EXACT")!=1 or lines.count("GP10_LIFT_END")!=1:return None
    a,b=lines.index("GP10_LIFT_EXACT"),lines.index("GP10_LIFT_END")
    if b-a-1!=len(polynomials):raise AlgebraError("CAS homogeneous cofactor count")
    cofs=[expanded_parse(ctx,line) for line in lines[a+1:b]]
    if sum((p*q for p,q in zip(polynomials,cofs)),ctx.constant(0))!=target:raise AlgebraError("dehomogenized identity failed")
    return cofs

def positivity(ctx, p):
    import sympy as sp
    used = sorted({i for e,c in p.terms() if c for i,power in enumerate(e) if power})
    if len(used) == 1:
        i = used[0]; x = sp.Symbol(ctx.names()[i])
        poly = sp.Poly(sum(sp.Rational(str(c))*x**int(e[i]) for e,c in p.terms()),x)
        if poly.degree() > 0 and poly.count_roots(-sp.oo,sp.oo) == 0:
            return {"sturm":ctx.names()[i][0]+"_"+ctx.names()[i][1:]}
    # Complete squares for a rational quadratic with a positive definite quadratic part.
    if any(sum(e)>2 for e,c in p.terms()):
        return None
    rem, squares = p, []
    for i in range(ctx.nvars()):
        xi = ctx.gen(i)
        terms = rem.to_dict(); exponent = tuple(2 if k==i else 0 for k in range(ctx.nvars()))
        coefficient = terms.get(exponent,fmpq(0))
        involving = {e:c for e,c in terms.items() if e[i]}
        if not involving:
            continue
        if coefficient <= 0:
            return None
        linear = ctx.constant(0)
        for e,c in involving.items():
            if e == exponent:
                continue
            if e[i] != 1:
                return None
            e2 = list(e); e2[i]-=1
            linear += ctx.from_dict({tuple(e2):c})
        q = xi + linear/(2*coefficient)
        rem -= coefficient*q*q
        squares.append([str(coefficient),sparse(q)])
    d = rem.to_dict()
    c = d.get((0,)*ctx.nvars(), fmpq(0))
    if len(d) != 1 or c <= 0:
        return None
    return {"sos":{"c":str(c),"squares":squares}}

def verify_algebra(code, cert):
    typ = cert.get("type")
    required = {"type","frame","sat","cofactors"}
    if typ == "real":
        required |= {"f"}
        if ("sturm" in cert) == ("sos" in cert):
            raise AlgebraError("real: need exactly one positivity proof")
        required |= {"sturm" if "sturm" in cert else "sos"}
    elif typ != "null":
        raise AlgebraError("algebra: invalid type")
    if set(cert) != required:
        raise AlgebraError("algebra: unexpected system or certificate field")
    ctx, _, gens = system(code,cert["frame"],cert["sat"])
    if not isinstance(cert["cofactors"],dict) or not set(cert["cofactors"]) <= set(gens):
        raise AlgebraError("cofactors: unexpected generator")
    total = ctx.constant(0)
    for k,v in cert["cofactors"].items():
        total += unsparse(ctx,v)*gens[k]
    f = ctx.constant(1) if typ=="null" else unsparse(ctx,cert["f"])
    if total != f:
        raise AlgebraError("identity: expansion is not the claimed target")
    if typ == "null":
        return True
    return verify_positivity(ctx,cert,f)

def verify_positivity(ctx,cert,f):
    if "sos" in cert:
        proof = cert["sos"]
        if set(proof) != {"c","squares"}:
            raise AlgebraError("sos: invalid fields")
        c = Fraction(proof["c"])
        if c <= 0:
            raise AlgebraError("sos: c must be positive")
        result = ctx.constant(fmpq(str(c)))
        for w,q in proof["squares"]:
            w = Fraction(w)
            if w <= 0:
                raise AlgebraError("sos: weight must be positive")
            result += fmpq(str(w))*unsparse(ctx,q)**2
        if result != f:
            raise AlgebraError("sos: expansion differs from f")
    else:
        import sympy as sp
        proof = cert["sturm"]
        if isinstance(proof,dict) and set(proof)=={"variable"}:
            # Read historical records written before check/FORMAT.md appeared.
            variable=proof["variable"]
        elif isinstance(proof,str):
            names={name[0]+"_"+name[1:]:name for name in ctx.names()}
            variable=names.get(proof)
        else:
            variable=None
        if variable not in ctx.names():
            raise AlgebraError("sturm: invalid variable")
        index = ctx.names().index(variable)
        if any(any(e[j] for j in range(ctx.nvars()) if j!=index) for e,c in f.terms()):
            raise AlgebraError("sturm: f is not univariate")
        x=sp.Symbol(variable)
        p=sp.Poly(sum(sp.Rational(str(c))*x**int(e[index]) for e,c in f.terms()),x)
        if p.is_zero or (p.degree()>0 and p.count_roots(-sp.oo,sp.oo)!=0):
            raise AlgebraError("sturm: real zero exists or constant polynomial")
    return True

def algebra_search(code, method, seconds, all_pairs=False, frame=None, extra_sat=(), variable_order=None, ordering="dp", fglm=False, trace=None, algorithm="std", dag=False, quadratic=False, quadratic_rows=250):
    trace = trace or (lambda stage: None)
    deadline = time.monotonic()+seconds
    n,edges = decode(code)
    if n<3 or not edges:
        return None, {"reason":"no eligible edge system"}
    frame = list(min(edges)) if frame is None else frame
    sat = [list(p) for p in sorted(set(choose_sat(n,edges,all_pairs)) | {tuple(p) for p in extra_sat})]
    ctx,coords,gens = system(code,frame,sat)
    trace("system")
    helpers = prepared_helpers(code,frame,sat,ctx,coords,gens)
    trace("preprocessed")
    polynomials = [p for p,c in helpers]
    remaining = lambda: max(0.001,deadline-time.monotonic())
    gb = basis(ctx,polynomials,remaining(),variable_order,ordering,algorithm)
    trace("basis")
    if fglm and method == "real" and ordering == "dp":
        gb += fglm_basis(ctx,gb,remaining(),variable_order=variable_order)
        trace("fglm")
    targets = []
    if method == "null":
        if ctx.constant(1) in gb:
            targets = [(ctx.constant(1),{})]
    else:
        for p in gb:
            for target in (p,-p):
                proof=positivity(ctx,target)
                if proof:
                    targets.append((target,proof));break
    quadratic_detail={}
    if (method=="portfolio" or quadratic) and not targets and remaining()>0.1:
        from quadratic_sos import discover
        discovered,quadratic_detail=discover(ctx,gb,coords,edges,min(1 if quadratic else 0.3,remaining()/3),max_rows=quadratic_rows,lens=quadratic)
        if discovered:
            targets.append(discovered);trace("quadratic-target")
    collision_tests=0
    if method=="portfolio" and not targets:
        # Zero remainder is only a target hint. lift and the DAG verifier prove it.
        for pair in itertools.combinations(range(n),2):
            if pair in edges or list(pair) in sat:continue
            distance=sum(((coords[pair[0]][j]-coords[pair[1]][j])**2 for j in (0,1)),ctx.constant(0))
            remainder=distance
            for iteration in range(100):
                changed=False
                for h in gb:
                    if not h:continue
                    quotient,remainder=divmod(remainder,h)
                    changed=changed or bool(quotient)
                if not changed or not remainder:break
            collision_tests+=1
            if remainder:continue
            trace("collision-target:"+str(pair))
            cofs=lift(ctx,polynomials,distance,remaining(),variable_order,ordering,algorithm)
            if cofs is None:continue
            from dag import collision_dag
            cert=collision_dag(code,frame,sat,ctx,helpers,cofs,distance,pair)
            if len(json.dumps(cert,separators=(",",":")))>8*1024*1024-1000:
                raise AlgebraError("collision DAG exceeds checker line budget")
            return cert,{"basis_size":len(gb),"helper_rows":len(helpers),"sat_pairs":len(cert["sat"]),"positive_targets":0,"collision_pair":list(pair),"collision_tests":collision_tests,"dag_rows":len(cert["rows"])}
    targets.sort(key=lambda item: (any(any(e[i] for i,name in enumerate(ctx.names()) if name.startswith("t")) for e,c in item[0].terms()), len(item[0].to_dict())))
    trace("targets:"+str(len(targets)))
    for target,proof in targets[:8]:
        cofs = lift(ctx,polynomials,target,remaining(),variable_order,ordering,algorithm)
        trace("lift:"+str(cofs is not None))
        if cofs is None:
            continue
        term_bound=sum(len(c.to_dict())*sum(len(p.to_dict()) for p in identity.values()) for c,(poly,identity) in zip(cofs,helpers))
        if dag is True or (dag=="auto" and term_bound>60000):
            from dag import build_dag,verify_dag
            cert=build_dag(ctx,frame,sat,helpers,cofs,target,proof)
            verify_dag(code,cert)
            if len(json.dumps(cert,separators=(",",":")))>8*1024*1024-1000:
                raise AlgebraError("DAG certificate exceeds checker line budget")
            return cert,{"basis_size":len(gb),"helper_rows":len(helpers),"sat_pairs":len(sat),"positive_targets":len(targets),"dag_rows":len(cert["rows"])}
        full = {}
        for c,(p,identity) in zip(cofs,helpers):
            add_scaled(full,identity,c)
        for k,c in zip(gens,cofs[len(helpers):]):
            if c:
                full[k]=full.get(k,ctx.constant(0))+c
        trace("flattened")
        estimated=sum(sum(7+ctx.nvars()+sum(len(str(int(x))) for x in e)+len(str(c)) for e,c in p.terms())+len(k)+6 for k,p in full.items())
        if estimated>8*1024*1024-20000:
            raise AlgebraError("certificate exceeds checker line budget")
        output_type=("null" if target==ctx.constant(1) else "real") if method=="portfolio" else method
        cert={"type":output_type,"frame":frame,"sat":sat,"cofactors":{k:sparse(v) for k,v in full.items() if v}}
        if output_type == "real":
            cert.update({"f":sparse(target),**proof})
        trace("serialized")
        verify_algebra(code,cert)
        trace("verified")
        return cert,{"basis_size":len(gb),"helper_rows":len(helpers),"sat_pairs":len(sat),"positive_targets":len(targets),"collision_tests":collision_tests,"quadratic_discovery":quadratic_detail}
    return None,{"reason":"no certifiable target in Groebner basis","basis_size":len(gb),"helper_rows":len(helpers),"sat_pairs":len(sat),"positive_targets":len(targets),"collision_tests":collision_tests,"quadratic_discovery":quadratic_detail}
