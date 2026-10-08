"""Order-ten adapters. All shared B11 producer sources stay unchanged."""
from common import *
from collections import deque
import ctypes
import subprocess
import numpy as np
from graph6 import canonicalize, decode_graph6, iter_edges, pair_index, adjacency_dict, is_biconnected
from control_b10_guard import B10, B10_SHA, DATA, Refused, refuse
import store as shared_store
from stages import Producers, POLICIES
from tu import TU


def f9_checker(scratch):
    if digest(GP / 'check/gp10check.py') != CHECKER_SHA:
        raise ValueError('frozen_checker_hash')
    kernel = ROOT / 'research/unit-distance-22/check/udcheck.py'
    if digest(kernel) != '63b7f1b5e641f130b559b67700da41297c469e0336f86a57360093cb3a0633de':
        raise ValueError('frozen_kernel_hash')
    ck = load('control51_frozen_checker', GP / 'check/gp10check.py')
    ck.SCRATCH = Path(scratch)
    ck.SCRATCH.mkdir(parents=True, exist_ok=True)
    return ck


class Poset:
    def __init__(self, directory, guard):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        if digest(B10) != B10_SHA:
            raise ValueError('frozen_B10_hash')
        self.codes = B10.read_text().splitlines()
        self.ids = {c: i for i, c in enumerate(self.codes)}
        native = HERE / 'control_b10_native.c'
        filt = ROOT / 'research/unit-distance-22/filter'
        # Always rebuild: a supplied B11 index is never opened or trusted.
        subprocess.run(['cc', '-O3', '-Wall', '-Wextra', str(native), '-lnauty', '-o', str(self.directory / 'build')], check=True)
        subprocess.run(['cc', '-O3', '-Wall', '-Wextra', '-DCONTROL_TU', '-shared', '-fPIC', '-I', str(filt),
                        str(native), str(filt / 'udfilter.c'), '-o', str(self.directory / 'tu.so')], check=True)
        subprocess.run([str(self.directory / 'build'), str(B10), str(self.directory / 'relations.bin')], check=True)
        row = np.dtype([('parent', '<u4'), ('child', '<u4'), ('map', 'u1', (10,))])
        self.rows = np.memmap(self.directory / 'relations.bin', dtype=row, mode='r')
        self.down = np.concatenate(([0], np.cumsum(np.bincount(self.rows['parent'], minlength=len(self.codes)))))
        self.up = np.concatenate(([0], np.cumsum(np.bincount(self.rows['child'], minlength=len(self.codes)))))
        self.reverse = np.argsort(self.rows['child'], kind='stable')
        self.edges = np.array([decode_graph6(c)[1].bit_count() for c in self.codes])
        guard.check()

    def neighbours(self, gid, verdict):
        indices = range(self.down[gid], self.down[gid+1]) if verdict == 'embedded' else self.reverse[self.up[gid]:self.up[gid+1]]
        for i in indices:
            row = self.rows[i]
            yield int(row['child' if verdict == 'embedded' else 'parent']), row['map'].tolist()

    def validate(self, codes):
        total = 0
        for code in codes:
            n, mask = decode_graph6(code)
            gid = self.ids[code]
            expected = {self.ids[c.g6] for a, b in iter_edges(n, mask)
                        if (c := canonicalize(n, mask & ~(1 << pair_index(n, a, b)))).g6 in self.ids}
            rows = list(self.neighbours(gid, 'embedded'))
            if expected != {child for child, _ in rows}:
                raise ValueError('B10_poset_neighbours')
            edges = set(iter_edges(n, mask))
            for child, mapping in rows:
                cn, cm = decode_graph6(self.codes[child])
                if sorted(mapping) != list(range(10)) or any(tuple(sorted((mapping[a], mapping[b]))) not in edges for a, b in iter_edges(cn, cm)):
                    raise ValueError('B10_poset_map')
                if (gid, mapping) not in list(self.neighbours(child, 'refuted')):
                    raise ValueError('B10_poset_reverse')
                total += 1
        return {'parents': len(codes), 'relations': total, 'status': 'PASS'}


class Store(shared_store.Store):
    def __init__(self, *args, **kwargs):
        # Constructor injection in this separate process only. No B11 source edit.
        original = shared_store.checker
        shared_store.checker = f9_checker
        try:
            super().__init__(*args, **kwargs)
        finally:
            shared_store.checker = original
        self.routes = np.zeros((len(self.poset.codes), 10), dtype='u1')

    def propagate(self, code):
        if code not in self.poset.ids:
            return
        root = self.poset.ids[code]
        verdict = self.decided[code]
        flag = 1 if verdict == 'embedded' else 2
        if self.seen[root]:
            if self.seen[root] != flag:
                raise self.ck.Rejection('embedded_refuted_conflict', code)
            return
        self.seen[root], self.roots[root] = flag, root
        self.routes[root] = np.arange(10)
        self.pending_tu.append(code)
        todo = deque([root])
        while todo:
            parent = todo.popleft()
            old_map = self.routes[parent].tolist()
            for child, mapping in self.poset.neighbours(parent, verdict):
                if self.seen[child]:
                    if self.seen[child] != flag:
                        raise self.ck.Rejection('embedded_refuted_conflict', self.poset.codes[child])
                    continue
                composed = [old_map[v] for v in mapping] if flag == 1 else [mapping[v] for v in old_map]
                self.routes[child], self.roots[child], self.seen[child] = composed, root, flag
                self.pending_tu.append(self.poset.codes[child])
                todo.append(child)
                if child in self.assigned and not self.has(self.poset.codes[child]):
                    self.accept({'g6': self.poset.codes[child], 'verdict': verdict,
                                 'cert': {'type': 'super' if flag == 1 else 'sub', 'g6': code, 'map': composed}}, 'propagation')
            self.guard.check()


class F9TU(TU):
    def __init__(self, poset):
        self.library = ctypes.CDLL(str(poset.directory / 'tu.so'))
        self.library.init.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.library.closure.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        if not self.library.init(str(DATA / 'forbidden-74.json').encode(), str(DATA / 'tu-gadgets.json').encode()):
            raise ValueError('F9_tu_database')

    def endpoint(self, code, store):
        refuse('historical_endpoint', code)

    def transport(self, code, closure, store):
        target = closure['g6']
        if not store.has(target) and target in store.poset.ids:
            gid = store.poset.ids[target]
            if store.seen[gid]:
                verdict = 'embedded' if store.seen[gid] == 1 else 'refuted'
                root = store.poset.codes[int(store.roots[gid])]
                store.accept({'g6': target, 'verdict': verdict, 'cert': {
                    'type': 'super' if verdict == 'embedded' else 'sub', 'g6': root,
                    'map': store.routes[gid].tolist()}}, 'tu_reuse:endpoint')
        if not store.has(target):
            return None
        if store.decided[target] == 'embedded':
            return {'g6': code, 'verdict': 'embedded', 'cert': {'type': 'super', 'g6': target, 'map': closure['old_to_new']}}
        return {'g6': code, 'verdict': 'refuted', 'cert': {'type': 'tu', 'steps': closure['steps'],
                'end': {'refuted': target, 'map': [closure['old_to_new'].index(v) for v in range(10)]}}}


class ControlProducers(Producers):
    def __init__(self, store, tu, bases):
        super().__init__(store, tu)
        self.bases = {}
        for code, row in bases.items():
            store.ck.check_canonical([code])
            store.check.verify(row)
            self.bases[code] = row['cert']

    def warm(self, stage):
        if stage.method in ('extension', 'rebase', 'host'):
            import lattice
            import extension  # Only pure extend_exact is used; index() is never called.
            return
        super().warm(stage)

    def base(self, code):
        if code not in self.bases:
            from lattice import search
            from exact import graph6
            n, edges = graph6(code)
            if n > 9:
                refuse('generated_base_order', code)
            cert, _ = search(n, edges, int.from_bytes(hashlib.sha256(code.encode()).digest(), 'big'), 'lattice18', 20000)
            if cert:
                self.store.ck.exact_embedding(self.store.ck.decode(code), cert)
                self.bases[code] = cert
        return self.bases.get(code)

    def extension(self, code, seconds, directory, alternatives):
        from extension import ext
        n, mask = decode_graph6(code)
        adjacency = adjacency_dict(n, mask)
        started = time.monotonic()
        detail = {'method': 'one_edge_alternative_B9_bases' if alternatives else 'degree_two_B9', 'attempts': []}
        for vertex in range(n):
            if len(adjacency[vertex]) != 2:
                continue
            keep = [v for v in range(n) if v != vertex]
            reverse = {v: i for i, v in enumerate(keep)}
            small = sum(1 << pair_index(9, reverse[a], reverse[b]) for a, b in iter_edges(n, mask) if vertex not in (a, b))
            if not alternatives and not is_biconnected(9, small):
                continue
            pairs = [None]
            if alternatives:
                degrees = [len(v) for v in adjacency_dict(9, small).values()]
                pairs = [(a, b) for b in range(9) for a in range(b) if not small >> pair_index(9, a, b) & 1]
                pairs.sort(key=lambda p: (min(degrees[v] for v in p), sum(degrees[v] for v in p), p))
            for pair in pairs:
                candidate_mask = small if pair is None else small | 1 << pair_index(9, *pair)
                if not is_biconnected(9, candidate_mask):
                    continue
                base = canonicalize(9, candidate_mask)
                exact = self.base(base.g6)
                if exact is None:
                    continue
                cert = {'type': 'exact', 'field': exact['field'], 'coords': [exact['coords'][base.old_to_new[v]] for v in range(9)]}
                left = seconds - (time.monotonic() - started)
                if left <= 0:
                    return None, dict(detail, reason='extension_budget')
                attempt = {'vertex': vertex, 'base': base.g6, 'added_edge': pair}
                detail['attempts'].append(attempt)
                try:
                    candidate, meta = ext.extend_exact(code, cert, vertex, keep, adjacency[vertex], directory, seconds=min(left, 6 if seconds > 3 else 1))
                    attempt.update(meta)
                    self.store.ck.exact_embedding(self.store.ck.decode(code), candidate)
                    return candidate, detail
                except Exception as exc:
                    attempt['reason'] = type(exc).__name__ + ':' + str(exc)[-200:]
        return None, dict(detail, reason='B9_placements_exhausted')

    def propose(self, code, stage):
        if stage.method == 'host':
            return unknown(code, 'no_eligible_host_order_at_most_9', stage.budget()), {'eligible_hosts': 0}
        if stage.method == 'msolve_long':
            # portfolio.framed has the sole remaining order-eleven constant:
            # 19-rank. Adapt its solver boundary to 2*n-3-rank in this process.
            import generic_escalated as gm
            from exact import graph6
            from rigid_system import generic_rank
            original = gm.msolve_stage
            def at_order(g, directory, k, seconds, frames, pins):
                return original(g, directory, 2*graph6(g)[0]-3-generic_rank(g)[0], seconds, frames, pins)
            gm.msolve_stage = at_order
            try:
                return super().propose(code, stage)
            finally:
                gm.msolve_stage = original
        if stage.method not in ('extension', 'rebase'):
            return super().propose(code, stage)
        directory = self.work / (stage.name + '-cases') / hashlib.sha256(code.encode()).hexdigest()[:16]
        directory.mkdir(parents=True, exist_ok=True)
        try:
            with timer(stage.seconds):
                cert, detail = self.extension(code, stage.seconds, directory, stage.method == 'rebase')
        except Deadline:
            cert, detail = None, {'reason': 'wall_budget'}
        if cert:
            return {'g6': code, 'verdict': 'embedded', 'cert': cert}, detail
        return unknown(code, detail['reason'], stage.budget()), detail


def run_policy(store, tu, bases, policy):
    producer = ControlProducers(store, tu, bases)
    measurements = []
    for stage in POLICIES[policy]:
        tu.drain(store)
        if store.db.execute('SELECT 1 FROM completed WHERE stage=?', (stage.name,)).fetchone():
            continue
        ordering = store.order(stage.name, 'up' if stage.method in ('tu', 'tree', 'null', 'real') else 'down')
        start = time.monotonic()
        before = store.counts()
        if ordering:
            producer.warm(stage)
        print(compact({'event': 'stage_start', 'stage': stage.name, 'eligible': len(ordering)}), flush=True)
        for gid in ordering:
            code = store.poset.codes[gid]
            if store.has(code):
                continue
            store.guard.check()
            token = store.lease(gid, stage.name, stage.seconds + 2*stage.check_seconds + 60)
            began = time.monotonic()
            previous_seq = store.db.execute('SELECT COALESCE(MAX(seq),0) FROM accepted').fetchone()[0]
            try:
                record, detail = producer.propose(code, stage)
                with timer(stage.check_seconds):
                    store.finish(gid, stage.name, token, record, stage.budget(), time.monotonic()-began, detail)
            except (Exception, Deadline) as exc:
                if isinstance(exc, store.ck.Rejection) and exc.reason == 'embedded_refuted_conflict':
                    raise
                detail = {'reason': 'attempt_error:' + type(exc).__name__, 'checker_error': str(exc)[-1000:]}
                record = unknown(code, detail['reason'], stage.budget())
                store.finish(gid, stage.name, token, record, stage.budget(), time.monotonic()-began, detail)
            # Also drain an endpoint accepted before a later parent failure.
            for (seed,) in store.db.execute("SELECT g6 FROM accepted WHERE seq>? AND origin!='propagation' ORDER BY seq", (previous_seq,)):
                store.propagate(seed)
            tu.drain(store)
            with (producer.work / (stage.name + '-stats.jsonl')).open('a') as stream:
                stream.write(compact({'g6': code, 'meta': detail}) + '\n')
            from graph6 import _canonicalize_cached
            _canonicalize_cached.cache_clear()
        store.coverage()
        store.db.execute('INSERT INTO completed VALUES (?)', (stage.name,))
        store.db.commit()
        row = {'stage': stage.name, 'wall_seconds': time.monotonic()-start,
               'decisions_including_propagation': before['unknown']-store.counts()['unknown'], 'counts': store.counts()}
        measurements.append(row)
        print(compact(dict(row, event='stage_complete')), flush=True)
    return measurements
