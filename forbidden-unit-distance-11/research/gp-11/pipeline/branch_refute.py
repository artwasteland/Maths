"""Exhaustive triangle selectors and staged real-DAG refutations.

Frames, elimination polynomials and collision covers are discovered from the
input graph. No graph identifiers, analyst certificates or target polynomials
are used. A failed branch leaves the whole graph UNKNOWN.
"""
from common import *
import itertools
import algebra as a
from flint import fmpq_poly as P
from late_stage import Budget, isolated, worker_main


def search(code, seconds, directory):
    return isolated(__file__, code, seconds, directory)


def degree(p):
    return max(map(sum, p.to_dict()), default=0)


def constant(p):
    return p.to_dict().get((0,)*p.context().nvars(), a.fmpq(0))


def add(co, key, value):
    if key is not None and value:
        co[key] = co.get(key, value.context().constant(0)) + value


class Pool:
    def __init__(self, ctx, sources):
        self.ctx = ctx
        self.zero = ctx.constant(0)
        self.one = ctx.constant(1)
        self.values = dict(sources)
        self.rows = []
        self.seen = {}

    def put(self, p, co):
        co = {key: q for key, q in co.items() if q}
        if sum((self.values[key]*q for key, q in co.items()), self.zero) != p:
            raise ValueError("producer_row_identity")
        if not p:
            return None, self.one
        scale = p.leading_coefficient()
        p /= scale
        key = str(p)
        if key in self.seen:
            return self.seen[key], scale
        ref = "aux:" + str(len(self.rows))
        self.rows.append((p, {key: q/scale for key, q in co.items()}))
        self.values[ref] = p
        self.seen[key] = ref
        return ref, scale

    def needed(self, ref):
        seen = set()
        def visit(key):
            if key is None or not key.startswith("aux:") or key in seen:
                return
            seen.add(key)
            for source in self.rows[int(key[4:])][1]:
                visit(source)
        visit(ref)
        return sorted(int(key[4:]) for key in seen)


def reduce(p, divisors):
    co = {}
    for _ in range(100):
        changed = False
        for q, ref, scale in divisors:
            # One coordinate of a triangle apex may already be fixed.
            if not q:
                continue
            v, p = divmod(p, q)
            if v:
                add(co, ref, v*scale)
                changed = True
        if not p or not changed:
            return p, co
    raise ValueError("polynomial_division_limit")


def prefix(ctx, polynomials):
    used = [name for i, name in enumerate(ctx.names()) if any(any(e[i] for e in p.to_dict()) for p in polynomials)]
    if not used:
        used = [ctx.names()[0]]
    return ("ring r=0,(" + ",".join(used) + "),dp;short=0;option(redSB);\nideal I="
            + ",".join(str(p).replace(" ", "") for p in polynomials) + ";\n"), used


def basis(ctx, polynomials, budget):
    source, _ = prefix(ctx, polynomials)
    source += 'ideal G=std(I);print("DIM "+string(dim(G)));print("BASIS");for(int i=1;i<=size(G);i++){print(string(G[i]));}print("END");quit;\n'
    lines = budget.tool(source, ".sing", ["Singular", "-q"], cap=20).splitlines()
    dimension = int(next(line[4:] for line in lines if line.startswith("DIM ")))
    return [a.expanded_parse(ctx, line) for line in lines[lines.index("BASIS")+1:lines.index("END")]], dimension


def small_lift(ctx, sources, target, budget):
    source, _ = prefix(ctx, [p for p, _, _ in sources])
    source += "ideal J=" + str(target).replace(" ", "") + ";matrix T=lift(I,J);\n"
    source += 'print("LIFT");for(int i=1;i<=nrows(T);i++){print(string(T[i,1]));}print("END");quit;\n'
    lines = budget.tool(source, ".sing", ["Singular", "-q"], cap=10).splitlines()
    values = [a.expanded_parse(ctx, line) for line in lines[lines.index("LIFT")+1:lines.index("END")]]
    if len(values) != len(sources):
        raise ValueError("lift_source_count")
    co = {}
    for (_, ref, scale), q in zip(sources, values):
        add(co, ref, scale*q)
    return co


def frame_order(code):
    n, edges = a.decode(code)
    sat = list(map(list, a.choose_sat(n, edges)))
    choices = []
    for edge in edges:
        ctx, cs, gens = a.system(code, list(edge), sat)
        helpers = a.prepared_helpers(code, list(edge), sat, ctx, cs, gens, False)
        nonlinear = [p for p, _ in helpers if degree(p) > 1]
        used = {i for p in nonlinear for ex in p.to_dict() for i, power in enumerate(ex) if power}
        common = sum(tuple(sorted((v, edge[0]))) in edges and tuple(sorted((v, edge[1]))) in edges for v in range(n))
        valence = sum(v in edge for e in edges for v in e)
        choices.append((len(used), -common, -valence, edge))
    return [list(item[-1]) for item in sorted(choices)]


def triangles(ctx, cs, edges, linear, h, rh):
    zero, one = ctx.constant(0), ctx.constant(1)
    points = {v: tuple(reduce(p, linear)[0] for p in xy) for v, xy in cs.items()}
    hvars = {i for ex in h.to_dict() for i, power in enumerate(ex) if power}
    def rigid(p):
        return all(not power or i in hvars for ex in p.to_dict() for i, power in enumerate(ex))
    choices = []
    seen = set()
    for triple in itertools.combinations(sorted(cs), 3):
        if not all(pair in edges for pair in itertools.combinations(triple, 2)):
            continue
        for c in triple:
            u, v = [w for w in triple if w != c]
            dx, dy = [points[v][j]-points[u][j] for j in (0, 1)]
            if not rigid(dx) or not rigid(dy) or all(rigid(p) for p in points[c]):
                continue
            options = []
            for sign in (-1, 1):
                options.append([divmod(points[u][0]+dx/2-sign*h*dy, rh)[1],
                                divmod(points[u][1]+dy/2+sign*h*dx, rh)[1]])
            axis = next(j for j in (1, 0) if options[0][j] != options[1][j])
            delta = options[1][axis]-options[0][axis]
            if degree(delta) == 0:
                inv = one/constant(delta)
            else:
                ratio, rem = divmod(delta, h)
                if rem or degree(ratio):
                    continue
                inv = 4*h/(3*constant(ratio))
            selector = divmod((points[c][axis]-options[0][axis])*inv, rh)[1]
            signature = str(selector)
            if signature in seen or str(one-selector) in seen:
                continue
            seen.add(signature)
            choices.append({"triangle": list(triple), "apex": c, "base": [u, v], "selector": selector,
                            "assumptions": [[points[c][j]-option[j] for j in (0, 1)] for option in options]})
            break
    return choices


def no_real_roots(p):
    sequence = [p, p.derivative()]
    if not sequence[-1]:
        return bool(p)
    while sequence[-1]:
        r = -(sequence[-2] % sequence[-1])
        if not r:
            break
        sequence.append(r)
    def variation(infinity):
        signs = [(1 if q[q.degree()] > 0 else -1) * (infinity**q.degree()) for q in sequence]
        return sum(x != y for x, y in zip(signs, signs[1:]))
    return variation(-1) == variation(1)


def projection(ctx, gb, variable, value, budget):
    source, names = prefix(ctx, gb)
    source += 'ideal G=I;attrib(G,"isSB",1);if(dim(G)!=0){print("SKIP");quit;}\n'
    if variable not in names:
        source += "ring t=0,(" + ",".join(names+[variable]) + "),dp;short=0;ideal K=imap(r,G)," + variable + "-(" + str(value).replace(" ", "") + ");K=std(K);\n"
        origin, ideal = "t", "K"
    else:
        origin, ideal = "r", "G"
    order = [name for name in names if name != variable] + [variable]
    source += "ring s=0,(" + ",".join(order) + "),lp;short=0;ideal H=fglm(" + origin + "," + ideal + ");\n"
    source += 'print("PROJECTION");print(string(H[1]));print("END");quit;\n'
    lines = budget.tool(source, ".sing", ["Singular", "-q"], cap=30).splitlines()
    if "SKIP" in lines:
        raise ValueError("positive_dimensional_branch")
    p = a.expanded_parse(ctx, lines[lines.index("PROJECTION")+1])
    ix = ctx.names().index(variable)
    if any(any(power and k != ix for k, power in enumerate(ex)) for ex in p.to_dict()):
        raise ValueError("projection_not_univariate")
    raw = P([0])
    for ex, coefficient in p.terms():
        raw[ex[ix]] = coefficient
    target = P([1])
    for factor, multiplicity in raw.factor()[1]:
        if no_real_roots(factor):
            target *= factor**multiplicity
    if target.degree() == 0:
        raise ValueError("no_root_free_factor")
    return sum((ctx.gen(ix)**k*c for k, c in enumerate(target)), ctx.constant(0))


def horner_remainder(ctx, target, variable, d, divisors):
    ix = ctx.names().index(variable)
    coefficients = {ex[ix]: c for ex, c in target.terms()}
    r = ctx.constant(0)
    for k in range(max(coefficients), -1, -1):
        r = reduce(ctx.gen(ix)*r + ctx.constant(coefficients.get(k, 0))*d, divisors)[0]
    return r


def collision_cover(ctx, cs, pairs, divisors, target, variable, budget):
    one, zero = ctx.constant(1), ctx.constant(0)
    distances = {tuple(pair): reduce(sum(((cs[pair[0]][j]-cs[pair[1]][j])**2 for j in (0, 1)), zero), divisors)[0] for pair in pairs}
    candidates = sorted((pair for pair, d in distances.items() if degree(d) or not d),
                        key=lambda pair: (len(distances[pair].to_dict()), pair))
    chosen = []
    d = one
    def vanishes(d):
        return not horner_remainder(ctx, target, variable, d, divisors)
    if vanishes(d):
        return []
    for _ in range(2):
        for pair in candidates:
            budget.remaining()
            d = reduce(d*distances[pair], divisors)[0]
            chosen.append(pair)
            if vanishes(d):
                break
        if vanishes(d):
            break
    if not vanishes(d):
        return None
    for pair in list(chosen):
        trial = list(chosen)
        trial.remove(pair)
        d = one
        for q in trial:
            d = reduce(d*distances[q], divisors)[0]
        if vanishes(d):
            chosen = trial
    return chosen


def staged(ctx, prev, pool, budget):
    source, _ = prefix(ctx, [p for p, _, _ in prev])
    source += "int a,b;\n"
    for bound in (3, 4, 5, 6):
        source += f'degBound={bound};matrix T{bound};ideal G{bound}=liftstd(I,T{bound});print("BASIS");\n'
        source += f'for(a=1;a<=size(G{bound});a++){{print(string(G{bound}[a]));}}print("TRANSFORM");\n'
        source += f'for(a=1;a<=ncols(T{bound});a++){{for(b=1;b<=nrows(T{bound});b++){{print(string(T{bound}[b,a]));}}}}print("END");I=G{bound};\n'
    source += "quit;\n"
    lines = budget.tool(source, ".sing", ["Singular", "-q"], cap=120).splitlines()
    i = 0
    while i < len(lines):
        if lines[i] != "BASIS":
            i += 1
            continue
        i += 1
        polynomials = []
        while lines[i] != "TRANSFORM":
            polynomials.append(a.expanded_parse(ctx, lines[i]))
            i += 1
        i += 1
        new = []
        for p in polynomials:
            co = {}
            for _, ref, scale in prev:
                add(co, ref, scale*a.expanded_parse(ctx, lines[i]))
                i += 1
            new.append((p, *pool.put(p, co)))
        if lines[i] != "END":
            raise ValueError("staged_transform_shape")
        prev = new
        i += 1
    return prev


def certificate(pool, final, code, frame, sat, variable):
    indices = pool.needed(final)
    if len(indices) > 256:
        raise ValueError("dag_row_limit:" + str(len(indices)))
    mapping = {"aux:"+str(i): "aux:"+str(j) for j, i in enumerate(indices)}
    # Unused saturation variables cost bytes in every monomial exponent vector.
    used_sources = {key for i in indices for key in pool.rows[i][1] if key.startswith("s:")}
    used_sat = [pair for pair in sat if "s:" + ",".join(map(str, pair)) in used_sources]
    n, _ = a.decode(code)
    keep = list(range(2*(n-2))) + [2*(n-2)+sat.index(pair) for pair in used_sat]
    removed = set(range(pool.ctx.nvars()))-set(keep)
    def sparse(p):
        if any(ex[j] for ex in p.to_dict() for j in removed):
            raise ValueError("unused_saturation_variable")
        return [[str(c), [int(ex[j]) for j in keep]] for ex, c in sorted(p.to_dict().items()) if c]
    return {"type": "real-dag", "frame": frame, "sat": used_sat,
            "rows": [{"poly": sparse(pool.rows[i][0]), "cofactors": {mapping.get(k, k): sparse(q) for k, q in pool.rows[i][1].items()}} for i in indices],
            "f": sparse(pool.values[final]), "sturm": variable[0] + "_" + variable[1:]}


def finish(pool, final, code, frame, sat, variable, budget):
    cert = certificate(pool, final, code, frame, sat, variable)
    size = len(compact(dict(g6=code, verdict="refuted", cert=cert)).encode())+1
    if size > MAX_RECORD:
        raise ValueError("record_limit:" + str(size))
    budget.detail.update(frame=frame, saturation_pairs=cert["sat"], rows=len(cert["rows"]), record_bytes=size,
                         selector_combination_row=len(cert["rows"])-1, reason="real_dag_refutation")
    return cert


def attempt(code, frame, budget):
    n, edges = a.decode(code)
    sat = list(map(list, a.choose_sat(n, edges, True)))
    ctx, cs, gens = a.system(code, frame, sat)
    zero, one = ctx.constant(0), ctx.constant(1)
    helpers = a.prepared_helpers(code, frame, sat, ctx, cs, gens, False)
    global_pool = Pool(ctx, gens)
    shared = [(p, *global_pool.put(p, co)) for p, co in helpers]
    for p, ref, _ in shared:
        if degree(p) == 0:
            budget.detail.update(branches=[{"choices": [], "pairs": [], "target": "1"}], triangle_choices=[])
            return finish(global_pool, ref, code, frame, sat, ctx.names()[0], budget)
    linear = [row for row in shared if degree(row[0]) <= 1]
    reduced_edges = {}
    for key, p in gens.items():
        if key.startswith("s:"):
            continue
        remainder, co = reduce(p, linear)
        if remainder:
            reduced_edges[key] = (remainder, *global_pool.put(remainder, {key: one, **{k: -q for k, q in co.items()}}))
    hs = [(p, ref, scale) for p, ref, scale in shared if degree(p) == 2 and len(p.to_dict()) == 2
          and constant(p) == -a.fmpq(3, 4)]
    choices = []
    if hs:
        rh, _, _ = hs[0]
        ex = next(ex for ex in rh.to_dict() if sum(ex))
        h = ctx.gen(next(i for i, power in enumerate(ex) if power))
        choices = triangles(ctx, cs, edges, linear, h, rh)
    if len(choices) > 3:
        raise ValueError("triangle_branch_limit")
    budget.detail.update(frame=frame, saturation_pairs=sat,
                         triangle_choices=[{key: value for key, value in choice.items() if key not in ("selector", "assumptions")} for choice in choices],
                         branches=[])
    budget.save()
    # Each local selector is proved to annihilate both equations of its branch.
    annihilators = []
    for choice in choices:
        sources = [row for key, row in reduced_edges.items() if set(map(int, key[2:].split(","))) <= set(choice["triangle"])]
        sources += hs[:1]
        sides = []
        for bit in (0, 1):
            selector = choice["selector"] if bit else one-choice["selector"]
            sides.append([global_pool.put(selector*p, small_lift(ctx, sources, selector*p, budget)) for p in choice["assumptions"][bit]])
        annihilators.append(sides)
    variable = ("y" if choices else "x") + str(next(v for v in range(n) if v not in frame))
    branches = []
    for bits in itertools.product((0, 1), repeat=len(choices)):
        assumptions = [p for choice, bit in zip(choices, bits) for p in choice["assumptions"][bit]]
        local = Pool(ctx, {**gens, **{"b:"+str(i): p for i, p in enumerate(assumptions)}})
        local_shared = [(p, *local.put(p, co)) for p, co in helpers]
        local_linear = [row for row in local_shared if degree(row[0]) <= 1]
        bl = [(p, "b:"+str(i), one) for i, p in enumerate(assumptions)]
        initial = []
        seen = set()
        for p, ref, scale in local_shared:
            remainder, co = reduce(p, bl+local_linear)
            if remainder and str(remainder) not in seen:
                initial.append((remainder, *local.put(remainder, {ref: scale, **{k: -q for k, q in co.items()}})))
                seen.add(str(remainder))
        if not initial:
            raise ValueError("empty_branch_system")
        gb, dimension = basis(ctx, [p for p, _, _ in initial], budget)
        divs = bl+local_linear+[(p, None, one) for p in gb]
        if dimension > 0:
            # Products can grow without bound in a positive-dimensional quotient.
            # Retain immediate collisions; FGLM below requires dimension zero.
            forced = next((pair for pair in sat if not reduce(sum(
                ((cs[pair[0]][j]-cs[pair[1]][j])**2 for j in (0, 1)), zero), divs)[0]), None)
            if forced is None:
                raise ValueError("positive_dimensional_branch:" + str(dimension))
            pairs = [tuple(forced)]
        else:
            pairs = collision_cover(ctx, cs, sat, divs, one, variable, budget)
        target = one
        if pairs is None:
            value = reduce(cs[int(variable[1:])]["xy".index(variable[0])], bl+local_linear)[0]
            target = projection(ctx, gb, variable, value, budget)
            pairs = collision_cover(ctx, cs, sat, divs, target, variable, budget)
        if pairs is None:
            raise ValueError("uncovered_real_branch:" + str(bits))
        row = dict(choices=list(bits), pairs=list(map(list, pairs)), target=str(target))
        budget.detail["branches"].append(row)
        budget.save()
        branches.append((bits, local, local_shared, bl, local_linear, initial, pairs, target))
    product = one
    for *_, target in branches:
        product *= target
    if degree(product) == 0:
        variable = ctx.names()[0]
    finals = []
    for bits, local, local_shared, bl, local_linear, initial, pairs, target in branches:
        last_basis = staged(ctx, initial, local, budget)
        divs = bl+local_linear+last_basis
        d, t = one, one
        invref, invscale = None, one
        for pair in pairs:
            dist = sum(((cs[pair[0]][j]-cs[pair[1]][j])**2 for j in (0, 1)), zero)
            inv = ctx.gen(2*(n-2)+sat.index(list(pair)))
            newd, co = reduce(d*dist, divs)
            newt = t*inv
            identity = {k: -newt*q for k, q in co.items()}
            add(identity, "s:"+",".join(map(str, pair)), one)
            add(identity, invref, inv*dist*invscale)
            invref, invscale = local.put(newt*newd-one, identity)
            d, t = newd, newt
        ix = ctx.names().index(variable)
        coefficients = {ex[ix]: c for ex, c in target.terms()}
        top = max(coefficients)
        part = ctx.constant(coefficients[top])
        r, co = reduce(part*d, divs)
        last, lastscale = local.put(part*d-r, co)
        for k in range(top-1, -1, -1):
            part = part*ctx.gen(ix)+ctx.constant(coefficients.get(k, 0))
            r, co = reduce(ctx.gen(ix)*r+ctx.constant(coefficients.get(k, 0))*d, divs)
            add(co, last, ctx.gen(ix)*lastscale)
            last, lastscale = local.put(part*d-r, co)
        if r:
            raise ValueError("staged_basis_insufficient")
        co = {}
        add(co, invref, -target*invscale)
        add(co, last, t*lastscale)
        lr, ls = local.put(target, co)
        selector = one
        for choice, bit in zip(choices, bits):
            selector *= choice["selector"] if bit else one-choice["selector"]
        mapping = {key: (key, selector) for key in gens}
        for (_, lref, lscale), (_, gref, gscale) in zip(local_shared, shared):
            mapping[lref] = (gref, selector*gscale/lscale)
        for i, (choice, bit) in enumerate(zip(choices, bits)):
            factor = choice["selector"] if bit else one-choice["selector"]
            other, rem = divmod(selector, factor)
            if rem:
                raise ValueError("selector_factor")
            for j, (ref, scale) in enumerate(annihilators[i][bit]):
                mapping["b:"+str(2*i+j)] = (ref, other*scale)
        for i in local.needed(lr):
            key = "aux:"+str(i)
            if key in mapping:
                continue
            p, cofactors = local.rows[i]
            co = {}
            for source, q in cofactors.items():
                ref, scale = mapping[source]
                add(co, ref, q*scale)
            mapping[key] = global_pool.put(selector*p, co)
        ref, scale = mapping[lr]
        quotient, remainder = divmod(product, target)
        if remainder:
            raise ValueError("branch_target_factor")
        finals.append((ref, scale*ls*quotient))
    co = {}
    for ref, q in finals:
        add(co, ref, q)
    final, _ = global_pool.put(product, co)
    return finish(global_pool, final, code, frame, sat, variable, budget)


def worker(request):
    detail = {"method": "branch_refute", "attempts": []}
    budget = Budget(request["seconds"]-.2, request["directory"], detail)
    budget.save()
    frames = frame_order(request["g6"])
    detail["candidate_frames"] = frames[:4]
    budget.save()
    for frame in frames[:2]:
        started = time.monotonic()
        try:
            cert = attempt(request["g6"], frame, budget)
            detail["attempts"].append(dict(frame=frame, seconds=time.monotonic()-started, result="refuted"))
            return cert, detail
        except Exception as exc:
            detail["attempts"].append(dict(frame=frame, seconds=time.monotonic()-started, reason=type(exc).__name__+":"+str(exc)[-250:]))
            budget.save()
    return None, dict(detail, reason="no_exhaustive_branch_certificate")


if __name__ == "__main__":
    worker_main(worker, search, 120)
