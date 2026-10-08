"""Bounded msolve producer. All acceptance is by exact.verify, never msolve status."""
from __future__ import annotations
import ast
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

os.environ['SYMPY_GROUND_TYPES'] = 'python'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
from flint import fmpq as Q, fmpq_poly as Poly
from exact import verify, CertificateError, textq, graph6

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/tmp/gp10-embed/round2')
ORIGINAL_SHA256 = 'c2722288d22c3a1eab00c0b818d0204d4a98104d059b2fd4ecb7343e8ef759fa'
BUFFER_BYTES = 1 << 20
PATCHES = [(0x5b6e, 0xbf), (0x5b7e, 0xbe), (0x5cf5, 0xbf), (0x5d43, 0xbe), (0x5fa4, 0xbe)]


def limits():
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        os.nice(15 - os.getpriority(os.PRIO_PROCESS, 0))
    cap = 1000000 * 1024
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = min(cap, hard) if hard != resource.RLIM_INFINITY else cap
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(SCRATCH)


class Deadline(BaseException):
    pass


class timer:
    def __init__(self, seconds): self.seconds = seconds
    def __enter__(self):
        self.old = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Deadline()))
        signal.setitimer(signal.ITIMER_REAL, self.seconds)
    def __exit__(self, *args):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self.old)


def sha(data): return hashlib.sha256(data).hexdigest()


def prepare_binary():
    """Reduce only the CLI header buffers, with exact binary/version guards.

    The shipped CLI first mallocs 2^30 bytes, then later callocs 2^30 bytes.
    Disassembly confirms the five patched immediates are the two allocations
    and their three fgets limits. Polynomial parsing and solver code are intact.
    All submitted input files are smaller than the new buffer size.
    """
    SCRATCH.mkdir(parents=True, exist_ok=True)
    source = Path('/usr/bin/msolve').read_bytes()
    if sha(source) != ORIGINAL_SHA256:
        raise ValueError('msolve:unrecognized_binary_do_not_patch')
    data = bytearray(source)
    for offset, opcode in PATCHES:
        expected = bytes([opcode]) + (1 << 30).to_bytes(4, 'little')
        if data[offset:offset + 5] != expected:
            raise ValueError('msolve:patch_signature')
        data[offset + 1:offset + 5] = BUFFER_BYTES.to_bytes(4, 'little')
    target = SCRATCH / 'msolve-small-input'
    if not target.exists() or target.read_bytes() != data:
        target.write_bytes(data)
        target.chmod(0o755)
    return target, {'original': '/usr/bin/msolve', 'original_sha256': sha(source),
        'executable_sha256': sha(data), 'patch_offsets': [hex(x + 1) for x, _ in PATCHES],
        'old_buffer_bytes': 1 << 30, 'new_buffer_bytes': BUFFER_BYTES,
        'reason': 'unmodified CLI segfaults after failed 1 GiB header allocation under contract cap'}


def parse_literal(source):
    """Parse msolve's list/rational grammar, without eval or floating point."""
    s = source.strip()
    if not s.endswith(':'):
        raise ValueError('parse:missing_terminator')
    tree = ast.parse(s[:-1].replace('^', '**'), mode='eval')
    def visit(node):
        if isinstance(node, ast.List): return [visit(v) for v in node.elts]
        if isinstance(node, ast.Constant) and type(node.value) in (int, str): return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = visit(node.operand)
            if not isinstance(value, (int, Fraction)): raise ValueError('parse:unary')
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            a, b = visit(node.left), visit(node.right)
            if not isinstance(a, (int, Fraction)) or not isinstance(b, (int, Fraction)):
                raise ValueError('parse:arithmetic')
            if isinstance(node.op, ast.Div): return Fraction(a) / Fraction(b)
            if isinstance(node.op, ast.Pow) and a == 2 and type(b) is int and 0 <= b <= 65536:
                return 2 ** b
        raise ValueError('parse:unsupported_syntax')
    return visit(tree.body)


def polynomial(raw):
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError('parse:polynomial')
    degree, coeff = raw
    if type(degree) is not int or degree < -1 or not isinstance(coeff, list):
        raise ValueError('parse:polynomial_degree')
    # msolve retains leading zero slots on some coordinate numerators.
    if len(coeff) != degree + 1 or any(type(c) is not int for c in coeff):
        raise ValueError('parse:polynomial_coefficients')
    return Poly(coeff)


def integer_coefficients(p):
    den = math.lcm(*(int(c.denominator) for c in p))
    coeff = [int(c * den) for c in p]
    g = math.gcd(*coeff)
    return [c // g for c in coeff]


def decode_output(source, variables, progress=None):
    raw = parse_literal(source)
    if raw == [-1]: return {'status': 'empty'}
    if (isinstance(raw, list) and len(raw) == 4 and raw[0] == 1
            and raw[1] == len(variables) and raw[2:] == [-1, []]):
        return {'status': 'positive_dimension'}
    if not isinstance(raw, list) or len(raw) != 3 or raw[0] != 0:
        raise ValueError('parse:unrecognized_status')
    par, real = raw[1:]
    if not isinstance(par, list) or len(par) != 6 or par[0] != 0:
        raise ValueError('parse:parametrization_header')
    names, form = par[3:5]
    if (not isinstance(names, list) or len(set(names)) != len(names)
            or par[1] != len(names) or not set(variables) <= set(names)
            or len(names) not in (len(variables), len(variables) + 1)
            or not isinstance(form, list) or len(form) != len(names)
            or any(type(c) not in (int, Fraction) for c in form)):
        raise ValueError('parse:variable_order_or_separator')
    added = len(names) == len(variables) + 1
    if added:
        if names[-1] in variables or not form[-1]:
            raise ValueError('parse:added_separator')
    elif form != [0] * (len(names) - 1) + [1]:
        raise ValueError('parse:coordinate_separator')
    nested = par[5]
    if not isinstance(nested, list) or len(nested) != 2 or nested[0] != 1:
        raise ValueError('parse:parametrization')
    p_raw, den_raw, nums = nested[1]
    p, den = polynomial(p_raw), polynomial(den_raw)
    degree = p.degree()
    if progress: progress({'degree': degree, 'ideal_degree': par[2], 'conversion_stage': 'header'})
    # Ideal degree includes multiplicities; the square-free eliminant may be smaller.
    if degree < 1 or type(par[2]) is not int or par[2] < degree:
        raise ValueError('parse:eliminant')
    if len(nums) != len(names) - 1:
        raise ValueError('parse:coordinate_count')
    if not isinstance(real, list) or len(real) != 2 or real[0] != 1:
        raise ValueError('parse:real_roots')
    boxes = real[1]
    if not isinstance(boxes, list): raise ValueError('parse:boxes')
    for box in boxes:
        if not isinstance(box, list) or len(box) != len(variables):
            raise ValueError('parse:box_dimension')
        for pair in box:
            if (not isinstance(pair, list) or len(pair) != 2
                    or any(type(q) not in (int, Fraction) for q in pair) or pair[0] > pair[1]):
                raise ValueError('parse:box_interval')
    if degree > 1024:
        return {'status': 'degree_cap', 'degree': degree, 'real_roots': len(boxes)}
    numerators = []
    for entry in nums:
        if not isinstance(entry, list) or len(entry) != 2 or type(entry[1]) is not int or not entry[1]:
            raise ValueError('parse:coordinate_denominator')
        numerators.append((polynomial(entry[0]), entry[1]))
    intervals = []
    if added:
        weights = {name: -Fraction(c) / Fraction(form[-1]) for name, c in zip(names[:-1], form[:-1])}
        for box in boxes:
            lower = upper = Fraction(0)
            for name, pair in zip(names[:-1], box):
                w = weights[name]
                a, b = Fraction(pair[0]) * w, Fraction(pair[1]) * w
                lower += min(a, b); upper += max(a, b)
            intervals.append([lower, upper])
    else:
        intervals = [box[-1] for box in boxes]
    return {'status': 'finite', 'p': p, 'den': den, 'numerators': numerators, 'form': form,
            'boxes': boxes, 'root_intervals': intervals, 'degree': degree,
            'separator': names[-1], 'added_separator': added, 'parameter_order': names, 'ideal_degree': par[2]}



def root_count(p):
    """Exact Sturm count of distinct real roots of a square-free Q polynomial."""
    sequence = [p, p.derivative()]
    while sequence[-1]:
        remainder = -(sequence[-2] % sequence[-1])
        if not remainder: break
        # Positive rescaling controls rational coefficient growth.
        scale = abs(remainder.leading_coefficient())
        sequence.append(remainder / scale)
    def changes(negative):
        signs = []
        for q in sequence:
            if not q: continue
            sign = 1 if q.leading_coefficient() > 0 else -1
            if negative and q.degree() % 2: sign = -sign
            signs.append(sign)
        return sum(a != b for a, b in zip(signs, signs[1:]))
    return changes(True) - changes(False)


def substitute(poly_dict, coordinate_polys, modulus):
    out = Poly([])
    for powers, coefficient in poly_dict.items():
        term = Poly([Q(coefficient.numerator, coefficient.denominator)])
        for exponent, coord in zip(powers, coordinate_polys):
            if exponent: term = (term * (coord ** exponent)) % modulus
        out = (out + term) % modulus
    return out


def certify(code, system, parsed):
    """Check parametrization equations and every candidate with local E-exact rules.

    Triage requires k=0, no pins, and an exhaustive zero-dimensional output.
    It is still a solver-dependent triage claim, never an R certificate.
    """
    meta = {'solver_status': parsed['status'], 'triage': False}
    unpinned = system['k'] == 0 and not system['pins']
    if parsed['status'] == 'empty':
        meta['triage'] = unpinned
        meta['reason'] = 'msolve_empty_unpinned' if unpinned else 'pinned_empty'
        return None, meta
    if parsed['status'] != 'finite':
        meta.update({key: parsed[key] for key in ('degree', 'real_roots') if key in parsed})
        meta['reason'] = 'msolve_' + parsed['status']
        return None, meta
    p = parsed['p']; boxes = parsed['boxes']
    meta.update(degree=p.degree(), real_roots=len(boxes), candidate_rejections=[])
    factors = sorted(p.factor()[1], key=lambda item: (item[0].degree(), tuple(str(c) for c in item[0])))
    real_counts = [root_count(f) for f, _ in factors]
    total_real = sum(real_counts)
    meta['sturm_real_roots'] = total_real
    if total_real != len(boxes): raise ValueError('parametrization:root_count')
    n, edges = graph6(code)
    a, b = system['frame']
    factor_status = []
    for (f, exponent), real_count in zip(factors, real_counts):
        if exponent != 1: raise ValueError('parametrization:repeated_factor')
        if f.degree() > 256:
            return None, dict(meta, reason='certificate_degree_cap', triage=False)
        den = parsed['den'] % f
        gcd, inverse, _ = den.xgcd(f)
        if gcd != Poly([1]): raise ValueError('parse:denominator_not_invertible')
        values = [(-((num % f) * inverse) / divisor) % f for num, divisor in parsed['numerators']]
        values.append(Poly([0, 1]) % f)
        names = parsed['parameter_order']
        functions = dict(zip(names, values))
        if parsed['added_separator']:
            relation = sum((functions[name] * Q(c.numerator, c.denominator)
                            if isinstance(c, Fraction) else functions[name] * c
                            for name, c in zip(names, parsed['form'])), Poly([])) % f
            if relation: raise ValueError('parse:separator_relation')
        coords = [(Poly([]), Poly([])) for _ in range(n)]
        coords[b] = (Poly([1]), Poly([]))
        for v in range(n):
            if v not in (a, b): coords[v] = (functions[f'x{v}'], functions[f'y{v}'])
        ordered = [functions[v] % f for v in system['variables']]
        for i, poly in enumerate(system['polynomials']):
            if substitute(poly, ordered, f):
                raise ValueError(f'parametrization:equation:{i}')
        points = [(x % f, y % f) for x, y in coords]
        collisions = []
        for v in range(n):
            for u in range(v):
                dx, dy = points[u][0] - points[v][0], points[u][1] - points[v][1]
                if not ((dx * dx + dy * dy) % f): collisions.append([u, v])
        factor_status.append({'degree': f.degree(), 'real_roots': real_count, 'coincidences': collisions})
        if not real_count or collisions: continue
        for index, interval in enumerate(parsed['root_intervals']):
            lo, hi = (Q(q.numerator, q.denominator) if isinstance(q, Fraction) else Q(q) for q in interval)
            if lo == hi and f(lo) == 0:
                if f.degree() != 1: raise ValueError('parametrization:rational_root_factor')
                lo, hi = lo - Q(1, 2**32), hi + Q(1, 2**32)
            elif f(lo) == 0 or f(hi) == 0:
                if f.degree() != 1: raise ValueError('parametrization:endpoint_root')
                root = lo if f(lo) == 0 else hi
                lo, hi = root - Q(1, 2**32), root + Q(1, 2**32)
            if f(lo) * f(hi) >= 0: continue
            d = f.degree()
            candidate = {'type': 'exact', 'field': {'minpoly': integer_coefficients(f),
                'interval': [textq(lo), textq(hi)]},
                'coords': [[[textq(c[i]) for i in range(d)] for c in point] for point in points]}
            try: candidate = verify(code, candidate, max_refinements=256)
            except CertificateError as exc:
                meta['candidate_rejections'].append({'root': index, 'reason': str(exc)})
                continue
            meta.update(reason='exact_embedding', certificate_degree=d, selected_box=index,
                        factors=factor_status)
            return candidate, meta
    meta['factors'] = factor_status
    meta['triage'] = unpinned and all(not f['real_roots'] or f['coincidences'] for f in factor_status)
    meta['reason'] = ('rigid_no_distinct_real_solution' if meta['triage'] else 'no_certified_candidate')
    return None, meta


def invoke(system, directory, seconds=20, parse=True):
    directory.mkdir(parents=True, exist_ok=True)
    text = system['text']
    if len(text.encode('ascii')) >= BUFFER_BYTES or '(' in text or ')' in text:
        raise ValueError('input:expansion_or_size')
    executable, provenance = prepare_binary()
    inp, out = directory / 'input.ms', directory / 'output.ms'
    inp.write_text(text, encoding='ascii')
    out.unlink(missing_ok=True)
    cmd = [str(executable), '-f', str(inp), '-o', str(out), '-P', '1', '-t', '1',
           '-p', '96', '-s', '12', '-l', '2', '-c', '2']
    seed_library = SCRATCH / 'msolve_seed.so'
    if not seed_library.exists(): raise ValueError('msolve:seed_library_not_built')
    env = dict(os.environ, LD_PRELOAD=str(seed_library),
               GP10_MSOLVE_SEED=str(int(sha(system['g6'].encode())[:8], 16)))
    started = time.monotonic()
    with (directory / 'solver.log').open('w') as log:
        child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            exitcode = child.wait(timeout=seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            child.kill(); exitcode = child.wait(); timed_out = True
        except BaseException:
            child.kill(); child.wait(); raise
    meta = {'command': cmd, 'msolve_seconds': time.monotonic() - started,
            'cap_seconds': seconds, 'returncode': exitcode, 'timeout': timed_out,
            'input_sha256': sha(inp.read_bytes()), 'binary': provenance,
            'seed': env['GP10_MSOLVE_SEED'], 'seed_library_sha256': sha(seed_library.read_bytes())}
    if timed_out: return None, dict(meta, reason='msolve_timeout')
    if exitcode != 0: return None, dict(meta, reason='msolve_crash_or_error')
    if not out.exists() or out.stat().st_size > 32 * 1024 * 1024:
        return None, dict(meta, reason='msolve_missing_or_oversize_output')
    raw = out.read_text()
    meta['output_sha256'] = sha(raw.encode())
    parsed = decode_output(raw, system['variables']) if parse else raw
    return parsed, meta
