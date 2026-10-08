#!/usr/bin/env python3
"""Portable checks for the five unit-distance deposits. Read NOTICE.md for scope."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / 'research'
WORK = ROOT / '.recheck-work'
DERIVED = ROOT / 'derived'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


@contextmanager
def stream(path):
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rb') as f:
            yield f
    elif path.suffix == '.zst':
        p = subprocess.Popen(['zstd', '-q', '-d', '-c', str(path)], stdout=subprocess.PIPE)
        try:
            yield p.stdout
        finally:
            p.stdout.close()
            code = p.wait()
            require(code == 0, 'zstd decompression failed')
    else:
        with path.open('rb') as f:
            yield f


def load(path):
    path = Path(path)
    if not path.exists() and path.with_name(path.name + '.gz').exists():
        path = path.with_name(path.name + '.gz')
    with stream(path) as f:
        return json.load(f)


def records(path):
    if isinstance(path, (list, tuple)):
        for p in path:
            yield from records(p)
        return
    with stream(path) as f:
        for raw in f:
            require(raw.endswith(b'\n') and raw != b'\n', 'malformed JSONL record')
            yield json.loads(raw)


def module(name, path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT), 'module is outside this deposit')
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def run(args, expected=None, cwd=ROOT):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    tail = (p.stdout.strip().splitlines() or [''])[-1]
    if tail:
        print(tail)
    require(p.returncode == 0, 'command failed: ' + ' '.join(map(str, args)) + '\n' + p.stderr[-1000:])
    if expected:
        require(expected in p.stdout, 'expected checker verdict missing: ' + expected)
    return p


def python(path, *args):
    return [sys.executable, '-I', '-B', str(path), *map(str, args)]


def environment():
    import flint
    import sympy
    import networkx
    require(sys.version_info[:2] == (3, 12), 'requires Python 3.12')
    require(flint.__version__ == '0.9.0', 'requires python-flint 0.9.0')
    require(sympy.__version__ == '1.14.0', 'requires sympy 1.14.0')
    require(shutil.which('nauty-labelg'), 'requires nauty-labelg on PATH')
    print(f'Environment: Python {sys.version.split()[0]}, python-flint {flint.__version__}, sympy {sympy.__version__}, networkx {networkx.__version__}; nauty-labelg')


def io_adapter(base):
    """Only compressed streaming and scratch placement change; proof routines stay frozen."""
    base.SCRATCH = WORK
    os.environ['TMPDIR'] = str(WORK)
    os.environ['SQLITE_TMPDIR'] = str(WORK)
    tempfile.tempdir = str(WORK)
    original_digest = base.digest

    def digest(path):
        path = Path(path)
        if path.suffix not in ('.gz', '.zst'):
            return original_digest(path)
        h = hashlib.sha256()
        with stream(path) as f:
            for raw in iter(lambda: f.read(1048576), b''):
                h.update(raw)
        return h.hexdigest()

    def lines(path):
        offset = 0
        with stream(path) as f:
            i = 0
            while True:
                raw = f.readline(base.MAX_LINE + 1)
                if not raw:
                    break
                i += 1
                base.need(len(raw) <= base.MAX_LINE, 'record_limit')
                base.need(raw.endswith(b'\n') and raw != b'\n', 'line_format')
                yield i, offset, raw
                offset += len(raw)

    base.lines = lines
    base.digest = digest


def gp_checker(order):
    d = RESEARCH / f'gp-{order}'
    obj = module('deposit_gpchecker', d / 'check' / f'gp{order}check.py')
    base = obj.base if order == 11 else obj
    io_adapter(base)
    return obj, base


def verify_refutations(obj, path, expected, only_refuted=False, forbidden_limit=None):
    checker = obj.Checker(forbidden_limit if forbidden_limit is not None else 9 if expected == 509 else 10)
    decisions, dependencies = {}, {}
    for row in records(path):
        if only_refuted and row['verdict'] != 'refuted':
            continue
        code = row['g6']
        require(code not in decisions and row['verdict'] == 'refuted', 'duplicate or non-refutation record')
        dep, detail = checker.verify(row)
        decisions[code] = 'refuted'
        if dep:
            dependencies[code] = dep
        if len(decisions) % 250 == 0:
            print(f'Refutation replay progress: {len(decisions)}/{expected}', flush=True)
    require(len(decisions) == expected, 'wrong refutation coverage')
    pending = dict(dependencies)
    accepted = set(decisions) - set(pending)
    while pending:
        ready = [code for code, target in pending.items() if target in accepted]
        require(ready, 'missing or cyclic refutation pointer')
        for code in ready:
            accepted.add(code)
            del pending[code]
    print(f'Refutations verified: {len(accepted)}; every pointer resolved to a checked refutation')
    return checker, decisions


def census_block_evidence(base, graph, max_order):
    """Frozen block rule, using the bound parent census for forbidden-freeness.

    Every block is a subgraph of its accepted F10-free parent. Thus the parent
    class receipt supplies the block's forbidden-freeness too. Reconstruct the
    remaining block preconditions and the complete edge/vertex evidence here;
    the frozen full-mode method repeats the forbidden search as well.
    """
    target = graph.nx()
    require(not base.nx.is_biconnected(target), 'block is biconnected')
    covered, evidence = set(), []
    for vertices in base.nx.biconnected_components(target):
        vertices = sorted(vertices)
        require(len(vertices) <= max_order <= 10, 'block order differs')
        edges = {tuple(sorted(e)) for e in target.subgraph(vertices).edges}
        require(not covered & edges, 'block edge overlap')
        covered.update(edges)
        evidence.append({'vertices': vertices, 'edges': [list(e) for e in sorted(edges)]})
    require(covered == graph.edges, 'block edge coverage differs')
    return {'blocks': evidence, 'isolated': list(base.nx.isolates(target))}


def gp_audit(order):
    obj, base = gp_checker(order)
    if order == 10:
        d = RESEARCH / 'gp-10/runs/B10-final-2026-09-25'
        published = d / 'L10.g6'
        evidence = d / 'minimality.jsonl'
        raw = RESEARCH / 'gp-10/cloud/lean3/records.jsonl.gz'
        verdicts = {}
        refutations = raw
        for row in records(raw):
            require(row['g6'] not in verdicts, 'duplicate candidate verdict')
            verdicts[row['g6']] = row['verdict']
        require(Counter(verdicts.values()) == {'embedded': 32653, 'refuted': 509}, 'B10 verdict coverage differs')
        expected = 509
    else:
        d = RESEARCH / 'gp-11/final-check-2026-10-08/checked'
        published = d / 'L11.g6'
        evidence = d / 'minimality.jsonl.gz'
        manifest = load(ROOT / 'REFUTATION-SOURCES.json')
        refutations = [ROOT / r['name'] for r in manifest['chunks']]
        require(len(refutations) > 0 and all(p.is_file() for p in refutations), 'missing GP-11 refutation chunk')
        for p, row in zip(refutations, manifest['chunks']):
            require(p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], 'GP-11 refutation chunk hash differs')
        verdicts = {}
        with stream(RESEARCH / 'gp-11/independent-checks-2026-10-07/audit/verdicts.tsv.gz') as f:
            import io
            for row in csv.DictReader(io.TextIOWrapper(f), delimiter='\t'):
                require(row['g6'] not in verdicts, 'duplicate independent candidate verdict')
                verdicts[row['g6']] = row['verdict']
        require(Counter(verdicts.values()) == {'embedded': 443444, 'refuted': 5264}, 'B11 independent verdict coverage differs')
        # Quick mode reuses the accepted census class receipt. Full mode repeats
        # the frozen forbidden-subgraph search. Bind every candidate, including
        # every deletion, to the exact independently enumerated input instead of
        # silently trusting the minimality record's graph class.
        frozen_input = RESEARCH / 'gp-11/data/B11.g6'
        frozen_sha = 'ec9a7109ae07ee7c1da853449d7c93d46587982ac75af3f9775bc89f8fc8937f'
        receipt = load(d / 'report.json')
        require(sha(frozen_input) == frozen_sha, 'frozen B11 census differs')
        require(receipt['status'] == 'ACCEPT' and receipt['profile'] == 'B11'
                and receipt['input_count'] == 448708
                and receipt['frozen_B11_sha256'] == frozen_sha,
                'accepted frozen B11 class receipt differs')
        census = frozen_input.read_text(encoding='ascii').splitlines()
        require(len(census) == 448708 and census == sorted(set(census))
                and set(census) == set(verdicts), 'independent verdicts do not cover the frozen B11 census')
        print('B11 candidate class: hash-pinned complete census and accepted historical class receipt; full mode repeats the class search', flush=True)
        expected = 5264
    refuted_codes = {c for c, v in verdicts.items() if v == 'refuted'}
    checker = obj.Checker(order - 1)
    rows = list(records(evidence))
    require(len(rows) == expected and len({r['g6'] for r in rows}) == expected, 'minimality record coverage differs')
    require({r['g6'] for r in rows} == refuted_codes, 'minimality and refutation sets differ')
    require(len(published.read_bytes().splitlines()) == (324 if order == 10 else 2833), 'published minimal-list coverage differs')
    derived = []
    for number, row in enumerate(rows, 1):
        code = row['g6']
        g = base.decode(code)
        require(g.n == order and base.nx.is_biconnected(g.nx()), 'minimality graph class')
        if order == 10:
            require(checker.contains_forbidden(g, order - 1) is None, 'minimality candidate contains an earlier forbidden graph')
        declared = {tuple(r['edge']): r for r in row['deletions']}
        require(len(declared) == len(row['deletions']) == len(g.edges) and set(declared) == g.edges, 'deletion coverage differs')
        codes, edges = [], []
        has_refuted = False
        for edge in sorted(g.edges):
            deletion = base.Graph(g.n, g.edges - {edge})
            rec = declared[edge]
            if base.nx.is_biconnected(deletion.nx()):
                edges.append(edge)
                codes.append(base.encode(deletion))
            else:
                blocks = census_block_evidence(base, deletion, order - 1) if order == 11 else checker.block_evidence(deletion, order - 1)
                require(rec == {'edge': list(edge), 'verdict': 'embedded_by_blocks', **blocks}, 'block-deletion evidence differs')
        for edge, child in zip(edges, base.canonical_many(codes)):
            verdict = verdicts.get(child)
            require(verdict in ('embedded', 'refuted'), 'missing or unknown deletion verdict')
            require(declared[edge] == {'edge': list(edge), 'g6': child, 'verdict': verdict}, 'deletion record disagrees with independently bound verdict: ' + child)
            has_refuted |= verdict == 'refuted'
        status = 'not_minimal' if has_refuted else 'minimal'
        require(row['status'] == status, 'recorded minimality status differs from derived status')
        if not has_refuted:
            derived.append(code)
        if number % 500 == 0:
            print(f'Minimality reconstruction progress: {number}/{expected}', flush=True)
    data = ''.join(c + '\n' for c in sorted(derived)).encode('ascii')
    DERIVED.mkdir(exist_ok=True)
    out = DERIVED / f'L{order}.g6'
    out.write_bytes(data)
    require(data == published.read_bytes(), 'derived list differs byte for byte from published list')
    require(len(derived) == (324 if order == 10 else 2833), 'wrong derived minimal count')
    _, proved = verify_refutations(obj, refutations, expected, only_refuted=(order == 10))
    require(set(proved) == refuted_codes, 'refutations disagree with independent verdict receipts')
    print(f'Minimality re-derived from {expected} deletion records; {len(derived)} graphs; published list byte-identical; sha256 {sha(out)}')
    print('Embedding verdicts used for minimality are saved receipts; full mode replays their certificates.')


def gp_quick(order):
    obj, base = gp_checker(order)
    summary = load(ROOT / 'MINIMALITY-SUMMARY.json')
    rows = summary['rows']
    require(summary['order'] == order and len(rows) == (509 if order == 10 else 5264), 'minimality summary coverage differs')
    require(len({r['g6'] for r in rows}) == len(rows), 'duplicate minimality summary graph')
    require(all(r['status'] in ('minimal', 'not_minimal') and r['deletions'] == len(base.decode(r['g6']).edges) for r in rows), 'invalid minimality summary')
    data = ''.join(r['g6'] + '\n' for r in sorted(rows, key=lambda r:r['g6']) if r['status'] == 'minimal').encode()
    path = RESEARCH / ('gp-10/runs/B10-final-2026-09-25/L10.g6' if order == 10 else 'gp-11/final-check-2026-10-08/checked/L11.g6')
    require(data == path.read_bytes(), 'published minimal list differs from separately shipped status summaries')
    scope = load(ROOT / 'QUICK-SCOPE.json')
    _, proved = verify_refutations(obj, ROOT / ('quick-refutations.jsonl.zst' if order == 10 else 'quick-refutations.jsonl.gz'), scope['records'], forbidden_limit=order-1)
    if order == 10:
        require(set(proved) == set(data.decode().splitlines()) and scope['records'] == 324, 'GP-10 minimal-member refutation coverage differs')
    else:
        scope = load(ROOT / 'QUICK-SCOPE.json')
        require(set(proved) == set(scope['selectedCodes']) and set(proved) <= set(data.decode().splitlines()), 'GP-11 bounded minimal-member sample differs')
        run(python(RESEARCH / 'gp-11/final-check-2026-10-08/verify_gate_evidence.py'), '34 evidence files match gates.json, 0 do not')
    DERIVED.mkdir(exist_ok=True)
    (DERIVED / f'L{order}.g6').write_bytes(data)
    print(f'Published L{order}: exact match to independently shipped status summaries; mathematical edge-deletion reconstruction belongs to --audit')


def gp_controls(order):
    obj, base = gp_checker(order)
    tree = ROOT / 'controls/tree/controls'
    names = sorted(p.name for p in tree.glob('*') if p.is_dir())
    require(set(['B4p','B5p','B6p','B7p','B8p','B9p']) <= set(names), 'archived census controls are missing')
    require(len(names) > 6, 'archived named/regression controls are missing')
    for name in names:
        folder = WORK / 'audit-controls' / name
        materialize_tree(tree / name, folder)
        if name in ['B4p','B5p','B6p','B7p','B8p','B9p']:
            (folder / (name + '.g6')).symlink_to(RESEARCH / 'gp-10/data' / (name + '.g6'))
        result = base.Run(folder, emit=lambda s: None).execute()
        require(result['status'] == 'ACCEPT' and result.get('control', {}).get('status') == 'PASS', 'archived control replay failed: ' + name)
    if order == 11:
        source = RESEARCH / 'gp-11/check/fixtures/named11'
        folder = WORK / 'audit-named11'
        shutil.copytree(source, folder)
        result = obj.Run(folder, emit=lambda s: None).execute()
        require(result['status'] == 'ACCEPT' and result.get('control', {}).get('status') == 'PASS', 'eleven-vertex named controls failed')
    print('Archived 4-through-9 and named/regression control certificates replayed independently')


def materialize_tree(source, target):
    if source.is_dir() and source.exists() and not hasattr(sys, '_deposit_archive_files'):
        shutil.copytree(source, target); return
    members = getattr(sys, '_deposit_archive_files', {})
    prefix = source.relative_to(ROOT).as_posix().rstrip('/') + '/'
    target.mkdir(parents=True, exist_ok=True)
    found = False
    for name in members:
        if not name.startswith(prefix): continue
        p = target / name[len(prefix):]
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((ROOT / name).read_bytes()); found = True
    require(found, 'missing archived control tree')


def prepare_b10(where):
    materialize_tree(ROOT / 'controls/tree', where)
    data = RESEARCH / 'gp-10/data'
    for profile in ['B4p', 'B5p', 'B6p', 'B7p', 'B8p', 'B9p']:
        (where / 'controls' / profile / (profile + '.g6')).symlink_to(data / (profile + '.g6'))
    (where / 'B10.g6').symlink_to(data / 'B10.g6')
    (where / 'UNKNOWN.g6').write_text('')
    (where / 'records.jsonl.gz').symlink_to(RESEARCH / 'gp-10/cloud/lean3/records.jsonl.gz')
    m = load(where / 'run.json')
    m['records'] = ['records.jsonl.gz']
    (where / 'run.json').write_text(json.dumps(m) + '\n')
    return where


def gp_full(order, args):
    obj, base = gp_checker(order)
    if order == 10:
        where = prepare_b10(WORK / 'b10')
        result = obj.Run(where, emit=lambda s: print(s) if s.startswith(('ACCEPT run', 'REJECT')) else None).execute()
        require(result['status'] == 'ACCEPT' and result['counts'] == {'embedded': 32653, 'refuted': 509, 'unknown': 0}, 'B10 full replay did not accept complete census')
        require((where / 'checked/L10.g6').read_bytes() == (RESEARCH / 'gp-10/runs/B10-final-2026-09-25/L10.g6').read_bytes(), 'full B10 minimal list differs')
    else:
        require(args.records is not None, 'full GP-11 requires --records gp11-b11-records.jsonl.zst downloaded beside the zip')
        path = args.records.resolve()
        require(path.stat().st_size == 550269076 and sha(path) == 'aee1dec28195bac1254adad74fef548260061ff16c31651544929bb36be49506', 'compressed GP-11 file differs from deposit manifest')
        require(base.digest(path) == '41731c987fade25c26b205fb02c809a2b75461ddeae852869ad61aab2804e114', 'GP-11 decompressed content hash differs')
        where = WORK / 'b11'
        where.mkdir()
        b10 = prepare_b10(where / 'controls/B10')
        # The frozen B11 preflight requires an accepted COMPLETE B10 receipt before replay.
        report = load(RESEARCH / 'gp-10/runs/B10-final-2026-09-25/report.json')
        (b10 / 'checked').mkdir(exist_ok=True)
        (b10 / 'checked/report.json').write_text(json.dumps(report) + '\n')
        shutil.copyfile(RESEARCH / 'gp-10/runs/B10-final-2026-09-25/L10.g6', b10 / 'checked/L10.g6')
        shutil.copytree(RESEARCH / 'gp-11/check/fixtures/named11', where / 'controls/named11')
        named = obj.Run(where / 'controls/named11', emit=print).execute()
        require(named['status'] == 'ACCEPT' and named.get('control', {}).get('status') == 'PASS',
                'named eleven-vertex controls did not pass their certificate replay')
        shutil.copyfile(RESEARCH / 'gp-11/PREDICTIONS.md', where / 'predictions.md')
        (where / 'records.jsonl.zst').symlink_to(path)
        (where / 'input.g6').symlink_to(RESEARCH / 'gp-11/data/B11.g6')
        (where / 'UNKNOWN.g6').write_text('')
        controls = {p: 'controls/B10/controls/' + p for p in base.CONTROL_ORDERS}
        controls.update(B10='controls/B10', named11='controls/named11', regressions='controls/B10/controls/regressions')
        m = {'profile': 'B11', 'input': 'input.g6', 'input_sha256': sha(RESEARCH / 'gp-11/data/B11.g6'), 'records': ['records.jsonl.zst'],
             'unknown': 'UNKNOWN.g6', 'controls': controls, 'predictions': {'path': 'predictions.md', 'sha256': sha(where / 'predictions.md')}}
        (where / 'run.json').write_text(json.dumps(m) + '\n')
        result = obj.Run(where, b11_sha256=m['input_sha256'], emit=lambda s: print(s) if s.startswith(('ACCEPT run', 'REJECT')) else None).execute()
        require(result['status'] == 'ACCEPT' and result['counts'] == {'embedded': 443444, 'refuted': 5264, 'unknown': 0}, 'B11 full replay did not accept complete census')
        require((where / 'checked/L11.g6').read_bytes() == (RESEARCH / 'gp-11/final-check-2026-10-08/checked/L11.g6').read_bytes(), 'full B11 minimal list differs')
    DERIVED.mkdir(exist_ok=True)
    shutil.copyfile(where / f'checked/L{order}.g6', DERIVED / f'L{order}.g6')
    (DERIVED / f'full-GP{order}-report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Full GP-{order} accepted: {result["input_count"]} records, minimal {result["minimal_count"]}; elapsed {result["elapsed_seconds"]:.3f} seconds')


def u22_quick():
    ud = RESEARCH / 'unit-distance-22'
    unknown = WORK / 'UNKNOWN.g6'
    unknown.write_text('')
    lower = ud / 'results/u22/lower-bound/config-22-60.certificate.jsonl'
    run(python(ud / 'check/udcheck.py', '--expect-n', 22, '--expect-m', 60, '--data-dir', ud / 'data', lower), 'embedded=1')
    top = ud / 'results/u22/cell-22-61'
    for name in ['s15of48', 's38of48']:
        run(python(ud / 'check/udcheck.py', '--graphs', top / f'{name}.22-61.g6', '--unknown-file', unknown,
                   '--expect-n', 22, '--expect-m', 61, '--data-dir', ud / 'data', top / f'{name}.22-61.certs.jsonl'), 'tu=2')
    run(python(ud / 'check/udcheck.py', '--graphs', top / 'all4.g6', '--unknown-file', unknown, '--expect-n', 22,
               '--expect-m', 61, '--data-dir', ud / 'data', top / 'all4.embedder.certs.jsonl'), 'refuted=4')
    import networkx as nx
    forbidden = load(ud / 'data/forbidden-74.json')
    seen = set()
    for rec in records(ud / 'delta4/filter-verdicts.jsonl'):
        code, w = rec['g6'], rec['witness']
        require(code not in seen and rec['verdict'] == 'forbidden', 'degree-four witness coverage')
        seen.add(code)
        g = nx.from_graph6_bytes(code.encode())
        pat, image = forbidden[w['index']], w['map']
        require(len(image) == 1 + max(max(e) for e in pat) and len(set(image)) == len(image), 'degree-four map is not injective')
        require(all(type(v) is int and 0 <= v < 22 for v in image), 'degree-four map range')
        require(all(g.has_edge(image[u], image[v]) for u, v in pat), 'degree-four map misses an edge')
    require(len(seen) == 18689 and seen == set((ud / 'delta4/children-22-61.g6').read_text().splitlines()), 'degree-four witness set differs')
    print('Degree-four lemma: 18,689 injective forbidden-subgraph maps rechecked')


def u23_quick():
    ud = RESEARCH / 'unit-distance-22'
    top = RESEARCH / 'unit-distance-23/results/u23/top-level/s50of1920'
    unknown = WORK / 'UNKNOWN.g6'
    unknown.write_text('')
    for name in ['udcheck.py', 'udcheck398.py']:
        run(python(ud / 'check' / name, '--graphs', top / '23-65.g6', '--unknown-file', unknown,
                   '--expect-n', 23, '--expect-m', 65, '--data-dir', ud / 'data', top / '23-65.certs.jsonl'), 'refuted=1')
    run(python(RESEARCH / 'unit-distance-23/blind-verifier/verify_tree.py', top / '23-65.g6', top / '23-65.certs.jsonl'), 'ACCEPT')


def u24_quick():
    obj, base = gp_checker(11)
    bundle = RESEARCH / 'unit-distance-24/survivor-s50'
    m = load(bundle / 'mapping.json')
    survivor, pattern = base.decode(m['survivor']), base.decode(m['pattern'])
    require((survivor.n, len(survivor.edges)) == (24, 69), 'survivor graph differs')
    require(sha(bundle / m['record']) == m['record_sha256'], 'survivor record hash differs')
    image = [m['pattern_to_survivor'][str(v)] for v in range(pattern.n)]
    base.mapping(pattern, survivor, image)
    row = load(bundle / m['record'])
    require(row['g6'] == m['pattern'] and row['verdict'] == 'refuted', 'survivor record identity')
    dep, _ = obj.Checker(10).verify(row)
    require(dep is None, 'survivor refutation must be direct')
    print('Survivor: injective 11-vertex subgraph map and frozen-checker refutation verified')


def funnel_check(order):
    mod = module('deposit_funnel', ROOT / 'evidence_check.py')
    mod.check(order, ROOT)


def enumeration_full(order, args):
    mod = module('deposit_enumeration', ROOT / 'enumeration_check.py')
    mod.check(order, ROOT, args.slice)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--quick', action='store_true')
    mode.add_argument('--full', action='store_true')
    mode.add_argument('--audit', action='store_true')
    ap.add_argument('--evidence', type=Path)
    ap.add_argument('--records', type=Path)
    ap.add_argument('--slice', type=int, default=0)
    try:
        args = ap.parse_args()
    except SystemExit as exc:
        if exc.code:
            print('FAIL')
        raise
    require(not WORK.exists(), '.recheck-work exists; remove the prior interrupted check workspace before retrying')
    WORK.mkdir()
    started = time.monotonic()
    good = False
    try:
        environment()
        os.environ['TMPDIR'] = str(WORK)
        os.environ['SQLITE_TMPDIR'] = str(WORK)
        tempfile.tempdir = str(WORK)
        order = int(ROOT.name.rsplit('-', 1)[1])
        expected = {22: 'full slice about 3 h 25 min in RESULT-u22.md',
                    23: 'saved aggregate 41.3 s, certificate 13.8 s, blind verifier 1.4 s; full slice median 556.8 s',
                    24: 'full slice 0 enumeration 1089 s, G4 108 s, chain 481.617 s, evidence 37.279 s',
                    10: 'full replay 3156.147 s in runs/B10-final-2026-09-25/report.json',
                    11: 'full replay 105407.900 s (about 29 hours) in final-check-2026-10-08/checked/report.json'}
        print('Recorded runtime reference: ' + expected[order] + '; see NOTICE.md for quick/full scope.')
        tier = 'quick' if args.quick else 'audit' if args.audit else 'full'
        print('Scope: ' + load(ROOT / 'RECHECK-SCOPES.json')[tier])
        def execute_tier():
            if ROOT.name.startswith('forbidden-unit-distance-'):
                if args.quick: gp_quick(order)
                elif args.audit:
                    gp_quick(order); gp_audit(order); gp_controls(order)
                else: gp_full(order, args)
            elif args.quick:
                {22: u22_quick, 23: u23_quick, 24: u24_quick}[order]()
            elif args.audit:
                {22: u22_quick, 23: u23_quick, 24: u24_quick}[order](); funnel_check(order)
            else: enumeration_full(order, args)
        if args.quick:
            require(args.evidence is None, '--quick does not take an evidence archive')
            execute_tier()
        else:
            require(args.evidence is not None, '--audit and --full require --evidence FILE downloaded beside the zip')
            archive = module('deposit_archive', ROOT / 'archive_io.py')
            with archive.mount(ROOT, args.evidence) as files:
                sys._deposit_archive_files = files
                try: execute_tier()
                finally: del sys._deposit_archive_files
        good = True
    except Exception as exc:
        print(f'Check failed: {type(exc).__name__}: {exc}')
    finally:
        shutil.rmtree(WORK)
    print(f'Elapsed: {time.monotonic() - started:.3f} seconds')
    print('PASS' if good else 'FAIL')
    return 0 if good else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'Check failed: {type(exc).__name__}: {exc}')
        print('FAIL')
        sys.exit(1)
