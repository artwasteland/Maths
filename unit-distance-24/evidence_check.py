"""Re-derive saved funnels and re-judge the portable u(24) receipt evidence.

This checks retained summaries, measurements and replay details. It does not replay
missing enumeration files or reconstruct the unlicensed Engel control catalogue.
"""
from collections import Counter, defaultdict
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

# The frozen structural validator uses the same cell regular expressions across
# thousands of receipts. Increase only the interpreter's bounded pattern caches.
re._MAXCACHE = 4096
re._MAXCACHE2 = 1024


def need(ok, why):
    if not ok:
        raise ValueError(why)


def load(path):
    path = Path(path)
    if not path.exists():
        path = path.with_name(path.name + '.gz')
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as f:
        return json.load(f)


def raw(path):
    path = Path(path)
    return gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def public_bindings(root, sources):
    transforms = {r['path']: r for r in load(root / 'PUBLICATION-TRANSFORMS.json')} if (root / 'PUBLICATION-TRANSFORMS.json').exists() else {}
    for item in sources['files']:
        rel = item['public'].split('/', 1)[1]
        path = root / rel
        need(path.is_file(), 'missing saved evidence: ' + rel)
        if rel in transforms:
            need(hashlib.sha256(path.read_bytes()).hexdigest() == transforms[rel]['publicSha256'], 'publication-transformed evidence changed: ' + rel)
        else:
            need(hashlib.sha256(raw(path)).hexdigest() == item.get('derivedContentSha256', item['sha256']) or hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], 'source evidence changed: ' + rel)
    print(f'Immutable evidence receipts checked: {len(sources["files"])} source blobs')


def counts_of(rows):
    need(len({(n, m) for n, m, ch, pc in rows}) == len(rows), 'duplicate count cell')
    return {(n, m): (ch, pc) for n, m, ch, pc in rows}


def valid_counts(rows, level):
    for n, m, children, pc in rows:
        need(type(children) is int and children >= 0, 'invalid children count')
        if n <= level:
            continue
        need(isinstance(pc, dict) and all(type(v) is int and v >= 0 for v in pc.values()), 'missing or invalid upper prune counts')
        need(pc['kept'] + pc['pruned'] == pc['input'] <= children, 'kept/pruned identity differs')
        kinds = [k for k in pc if re.fullmatch(r'tu|refuted|forbidden|[a-z0-9]+_(tu|refuted)', k)]
        need(sum(pc[k] for k in kinds) == pc['pruned'], 'prune-kind sum differs')


def original_funnel(root, sources):
    copies = defaultdict(list)
    for item in sources['copies']:
        rows = load(root / item['directory'] / 'counts.json')
        copies[item['slice']].append(counts_of(rows))
    need(set(copies) == set(range(48)), 'original u22 slice coverage differs')
    totals = defaultdict(lambda: [0, 0, 0])
    for i, cs in copies.items():
        need(all(c == cs[0] for c in cs), 'original u22 duplicate counts differ')
        for (n, m), (children, pc) in cs[0].items():
            if n >= 14 and isinstance(pc, dict):
                totals[n][0] += children
                totals[n][1] += pc['kept']
        for n in {n for n, m in cs[0] if n >= 14}:
            totals[n][2] += 1
    expected = load(root / 'research/unit-distance-22/results/u22/final-levels.json')
    for row in expected['levels']:
        need(totals[row['n']] == [row['children'], row['kept'], row['slices']], 'original u22 funnel differs at level ' + str(row['n']))
    need(expected['finished_slices'] == list(range(48)), 'published u22 coverage differs')
    print('Original u22 funnel re-derived from 48 slice counts; duplicate copies agree')
    print('Original summary audit retains nine unresolved entries; this count audit does not close those gaps.')


def u23_funnel(root, sources, aggregate23):
    expected = load(root / 'research/unit-distance-23/results/u23/result-inputs/aggregate.json')
    chosen, copies, prefix = {}, defaultdict(list), None
    for item in sources['copies']:
        d = root / item['directory']
        rows, summary, hashes = load(d / 'counts.json'), load(d / 'run-summary.json'), load(d / 'hashes.json')
        need(summary['slice'] == [12, item['slice'], 1920] and summary['target'] == [23, 65] and summary['completed_through_n'] == 23, 'u23 summary identity differs')
        current = counts_of(rows)
        summarized = {(e['n'], e['m']): (e.get('children'), (e.get('prune') or {}).get('counts')) for e in summary['levels']}
        need(current == summarized, 'u23 counts differ from separately stored summary')
        valid_counts(rows, 12)
        pre = {name: row['sha256'] for name, row in hashes['files'].items() if int(name.split('-')[0]) <= 12}
        if prefix is None:
            prefix = pre
        need(pre == prefix and len(pre) == 70, 'u23 common prefix hashes differ')
        kept = (d / '23-65.keep.g6').read_bytes()
        measured = hashes['files'].get('23-65.keep.g6')
        need(measured is not None and measured['sha256'] == hashlib.sha256(kept).hexdigest() and measured['records'] == kept.count(b'\n'), 'u23 saved survivor differs from hash receipt')
        candidate = {'counts': {(n, m): aggregate23.row(ch, pc) for n, m, ch, pc in rows},
                     'upper': {name: (r['sha256'], r['records']) for name, r in hashes['files'].items() if int(name.split('-')[0]) > 12}, 'keep_lines': set(kept.decode().splitlines())}
        copies[item['slice']].append(candidate)
        if item['chosen']:
            need(item['slice'] not in chosen, 'duplicate chosen u23 slice')
            need(expected['slices'][str(item['slice'])]['chosen'] == item['worker'], 'u23 selection differs from independently stored aggregate')
            chosen[item['slice']] = candidate
    need(set(chosen) == set(range(1920)), 'u23 chosen-slice coverage differs')
    for i, cs in copies.items():
        need(not any(aggregate23.compare_copies(cs[0], c) for c in cs[1:]), 'u23 duplicated slice disagrees')
    table, _ = aggregate23.aggregate(chosen, 12, (23, 65))
    need(table == expected['tree'], 'u23 re-derived funnel differs from published aggregate')
    kept = {i: sorted(c['keep_lines']) for i, c in chosen.items() if c['keep_lines']}
    published = (root / 'research/unit-distance-23/results/u23/top-level/s50of1920/23-65.g6').read_text().splitlines()
    need(kept == {50: published} and len(published) == 1, 'u23 survivor set differs from checked certificate')
    print(f'u23 funnel re-derived by the original aggregator: {len(chosen)} slices, {sum(map(len, copies.values()))} copies; one survivor in slice 50')


def u24_judge(root, sources, aggregate23):
    tools = root / 'research/unit-distance-24/tools'
    sys.path.insert(0, str(tools))
    import judge
    import evidence
    import receipt_audit
    import known_graphs
    judge.PILOT = root / 'plans/u24-pilot-plan.json'
    judge.FULL = root / 'plans/u24-full-plan.json'
    judge.PHASEB = root / 'plans/u24-phaseb-plan.json'
    judge.REPRO = root / 'plans/u24-repro-plan.json'
    plans = {name: load(root / f'plans/u24-{name}-plan.json') for name in ['pilot', 'full', 'phaseb', 'repro']}
    owners = {name: judge.plan_owners(p) for name, p in plans.items()}
    assigned = {name: set(judge.plan_check(p)) for name, p in plans.items()}
    need([len(assigned[n]) for n in ['pilot', 'full', 'phaseb', 'repro']] == [42, 1841, 37, 50], 'u24 plan sizes differ')
    need(not (assigned['pilot'] & assigned['full'] or assigned['pilot'] & assigned['phaseb'] or assigned['full'] & assigned['phaseb']) and set.union(*(assigned[n] for n in ['pilot', 'full', 'phaseb'])) == set(range(1920)), 'u24 production plans do not partition the slices')
    manifests = load(root / 'MANIFEST-PACKS.json')
    transformations = {r['path']: r for r in load(root / 'PUBLICATION-TRANSFORMS.json')}
    for pack in manifests['packs']:
        path = root / pack['name']
        expected = transformations.get(pack['name'], {}).get('publicSha256', pack['sha256'])
        need(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'deduplicated manifest pack changed')
    pack_cache = {}
    def manifest_text(digest):
        name = manifests['lookup'][digest]
        if name not in pack_cache:
            # Keep a bounded cache. Each pack's uncompressed text is below 16 MB.
            if len(pack_cache) >= 4:
                pack_cache.pop(next(iter(pack_cache)))
            pack_cache[name] = load(root / name)
        return pack_cache[name][digest]
    structure_sources = {r['sha256']: r for r in sources['files'] if r['path'].endswith('.structure.json')}
    prefix_cache = {}
    def inherited_prefix(structure, receipt, seen=()):
        binding = structure.get('prefix_receipt')
        if not binding:
            need('CHAIN OK' in raw(receipt).decode().splitlines(), 'whole prefix maker has no accepted chain receipt')
            return {}
        digest = binding['sha256']
        need(digest not in seen and digest in structure_sources, 'missing or cyclic whole-prefix source binding: ' + binding['name'])
        source = structure_sources[digest]
        need(Path(source['path']).name == binding['name'], 'prefix receipt name differs from immutable source')
        path = root / source['public'].split('/', 1)[1]
        prefix_receipt = path.with_name(path.name.replace('.structure.json.gz', '.txt.gz'))
        current = re.search(r'^# shared prefix digest: ([0-9a-f]{64});', raw(receipt).decode(), re.M)
        previous = re.search(r'^# shared prefix digest: ([0-9a-f]{64});', raw(prefix_receipt).decode(), re.M)
        need(current and previous and current[1] == previous[1], 'prefix graph digest differs from whole check')
        if digest not in prefix_cache:
            prior = load(path)
            need(prior['result'] == 'OK' and prior['target'] == [24, 69], 'prefix structural receipt is not accepted')
            inventory_path = path.with_name(path.name.replace('.structure.json.gz', '.inventory.jsonl.gz'))
            rows = receipt_audit.InventoryFiles(inventory_path, prior).rows
            inherited = inherited_prefix(prior, prefix_receipt, (*seen, digest))
            for name, row in inherited.items():
                need(name not in rows or rows[name] == row, 'prefix file differs across bound receipts')
                rows[name] = row
            # Use the original validator's prefix compatibility scope. Every
            # source copy is also structurally and mathematically audited below.
            prefix_cache[digest] = {name: row for name, row in rows.items()
                if (match := re.match(r'(?:shards/|_parents/)?(\d+)-\d+(?:[./]|$)', name))
                and int(match[1]) <= 12 and '.slice-' not in name}
        return prefix_cache[digest]
    snapshots, by_slice = {}, defaultdict(list)
    chain = module('deposit_u24_chain', root / 'research/unit-distance-22/enum/verify-chain-u24.py')
    source_by_public = {r['public'].split('/', 1)[1]: r for r in sources['files']}
    for number, item in enumerate(sources['copies'], 1):
        d = root / item['directory']
        rows, summary, config, reach, hashes = (load(d / n) for n in ['counts.json', 'run-summary.json', 'run-config.json', 'reach.json', 'hashes.json'])
        need(summary['slice'] == config['slice'] == [12, item['slice'], 1920] and summary['target'] == config['target'] == [24, 69] and summary['completed_through_n'] == 24, 'u24 snapshot identity differs')
        valid_counts(rows, 12)
        need(counts_of(rows) == {(e['n'], e['m']): (e.get('children'), (e.get('prune') or {}).get('counts')) for e in summary['levels']}, 'u24 counts differ from saved run summary')
        known_graphs.production_reach(reach)
        required = {'seed_n': 10, 'reach': True, 'reach_root_k': 5, 'prune': True, 'prune_from': 12, 'prune_filter_only': True,
                    'forbidden_set': 398, 'verify_stages': True, 'triangles': True, 'prune_filter_set': 74}
        need(all(config.get(k) == v for k, v in required.items()), 'u24 production configuration differs')
        files = sorted((d / 'receipts').glob('*.structure.json.gz'))
        need(len(files) == 1, 'u24 receipt identity missing or ambiguous')
        structure = load(files[0])
        need(structure['result'] == 'OK' and structure['slice'] == config['slice'] and structure['target'] == config['target'], 'u24 structural receipt differs')
        derived = evidence.requirements(config, summary, reach)
        evidence.require_structure(summary, structure['summary'])
        inventory_path = files[0].with_name(files[0].name.replace('.structure.json.gz', '.inventory.jsonl.gz'))
        inventory = receipt_audit.InventoryFiles(inventory_path, structure)
        receipt_path = files[0].with_name(files[0].name.replace('.structure.json.gz', '.txt.gz'))
        receipt_text = raw(receipt_path).decode()
        whole = 'CHAIN OK' in receipt_text.splitlines()
        need('# u24-worker verdict: pass' in receipt_text.splitlines()
             and f'sha256 {hashlib.sha256(receipt_audit.worker.CHECKER.read_bytes()).hexdigest()}' in receipt_text
             and not receipt_audit.worker.check_accept(receipt_text, 0 if whole else 3, item['slice'], whole),
             'u24 text receipt is not an accepted pinned whole or partial check')
        for label, path in [('structure receipt', files[0]), ('inventory', inventory_path),
                            ('known receipt', files[0].with_name(files[0].name.replace('.structure.json.gz', '.known.json.gz')))]:
            original_sha = source_by_public[path.relative_to(root).as_posix()]['sha256']
            need(re.search(rf'^# {label}: sha256 {original_sha},', receipt_text, re.M),
                 'u24 text receipt does not bind original ' + label)
        need(structure['run_summary_sha256'] == source_by_public[(d / 'run-summary.json.gz').relative_to(root).as_posix()]['sha256'],
             'u24 structural receipt names another original run summary')
        for name, row in inherited_prefix(structure, receipt_path).items():
            need(name not in inventory.rows or inventory.rows[name] == row, 'partial receipt differs from bound whole-prefix measurement')
            inventory.rows[name] = row
        # Publication redacts machine paths in embedded JSON manifest text. Check
        # its normalized digest and size, then use the unchanged structural rules.
        normalized = copy.deepcopy(structure)
        for name, row in normalized['manifests'].items():
            if 'textBlob' in row:
                row['text'] = manifest_text(row.pop('textBlob'))
            content = row['text'].encode()
            row['sha256'] = hashlib.sha256(content).hexdigest()
            inventory.rows[name] = {'sha256': row['sha256'], 'bytes': len(content), 'records': content.count(b'\n')}
        receipt_audit.check_structure(normalized, summary, config, derived, inventory)
        if structure.get('prefix_receipt'):
            prefix_source = structure_sources[structure['prefix_receipt']['sha256']]
            prefix = load(root / prefix_source['public'].split('/', 1)[1])
            older = {(e['n'], e['m']): e for e in prefix['summary']['levels']}
            for entry in structure['summary']['levels']:
                if config['seed_n'] < entry['n'] <= config['slice'][0]:
                    need(all(entry[k] == older[entry['n'], entry['m']][k] for k in
                             ['parent_sources', 'parent_edge_counts', 'parents', 'reach_k', 'shards']),
                         'partial receipt prefix structure differs from whole check')
        for e in structure['summary']['levels']:
            n, m = e['n'], e['m']
            if (n, m) not in derived['required']:
                continue
            cell = f'{n}-{m}'
            need(e['children'] == inventory.count(cell + '.g6'), 'u24 measured children differ')
            if n >= 12:
                pc = e['prune']['counts']
                need(pc['input'] == inventory.count(cell + '.reach.g6') == inventory.count(cell + '.certs.jsonl'), 'u24 measured certificate coverage differs')
                need(pc['kept'] == inventory.count(cell + '.keep.g6') and pc['unknown'] == inventory.count(cell + '.UNKNOWN.g6'), 'u24 measured keep/unknown differs')
        fp, replay = load(d / 'replay/fingerprint.json'), load(d / 'replay/summary.json')
        need(fp == structure['g4'] and replay.get('fraction') == 0.002, 'u24 G4 fingerprint or sample policy differs')
        entries = {(e['n'], e['m']): e for e in structure['summary']['levels']}
        shares = {int(re.fullmatch(r'\d+-(\d+)\.slice-\d+-of-\d+\.g6', n)[1]): r['records'] for n, r in structure['file_counts'].items() if '.slice-' in n}
        verdict, reasons = chain.g4_verdict(fp, replay, structure['slice'], {'required': entries}, entries, shares)
        need(verdict in ('PASS', 'EMPTY') and verdict == fp['result'] and not reasons, 'u24 detail-derived G4 verdict failed: ' + '; '.join(reasons))
        kept = (d / '24-69.keep.g6').read_bytes()
        measured = hashes['files']['24-69.keep.g6']
        need(measured['sha256'] == hashlib.sha256(kept).hexdigest() and measured['records'] == kept.count(b'\n'), 'u24 survivor bytes differ from saved measurement')
        known = load(files[0].with_name(files[0].name.replace('.structure.json.gz', '.known.json.gz')))
        need(known['result'] == 'OK' and known['problems'] == [] and known['slice'] == config['slice'], 'saved known-configuration control receipt failed')
        candidate = {'slice': item['slice'], 'worker': item['worker'], 'counts': {(n, m): aggregate23.row(ch, pc) for n, m, ch, pc in rows},
                     'upper': {name: (r['sha256'], r['records']) for name, r in hashes['files'].items() if int(name.split('-')[0]) > 12},
                     'keep_lines': set(kept.decode().splitlines()), 'prefix': tuple(sorted((name, r['sha256']) for name, r in hashes['files'].items() if int(name.split('-')[0]) <= 12)),
                     'options': {k: v for k, v in config.items() if k != 'slice'}, 'structure': {'target_files': structure['target_files'], 'g4': fp}}
        snapshots[item['slice'], item['worker']] = candidate
        by_slice[item['slice']].append(candidate)
        if number % 250 == 0:
            print(f'Portable u24 judge progress: {number}/{len(sources["copies"])} saved copies', flush=True)
    differences, _ = judge.compare_copies(by_slice)
    need(not differences, 'u24 copies disagree: ' + '; '.join(differences[:3]))
    main = {}
    def is_owner(worker, tag):
        worker, tag = worker.removeprefix('codex-'), tag.removeprefix('codex-')
        return worker == tag or worker.startswith(tag + '-')
    for name in ['pilot', 'full', 'phaseb']:
        for i, tag in owners[name].items():
            found = [c for (j, w), c in snapshots.items() if j == i and is_owner(w, tag)]
            need(found, f'u24 owner evidence missing: {name} s{i} {tag}')
            main[i] = found[0]
    for i, tag in owners['repro'].items():
        fresh = [c for (j, w), c in snapshots.items() if j == i and is_owner(w, tag)]
        need(fresh and not aggregate23.compare_copies(main[i], fresh[0]), f'u24 reproduction mismatch or missing: s{i}')
    table, _ = aggregate23.aggregate(main, 12, (24, 69))
    # Compare with the independently archived result table, not with a table
    # produced during this check. Preserve the original u24 table's field shape.
    expected_tree = load(root / 'research/unit-distance-24/result-values.json')['v']['tree']['value']
    levels = []
    for row in table['levels']:
        ms = sorted(c['m'] for c in table['cells'] if c['n'] == row['n'])
        levels.append({'level': row['n'], 'window': str(ms[0]) if len(ms) == 1 else f'{ms[0]}..{ms[-1]}',
                       'cells': row['cells'], 'children': row['children'], **row['counts'],
                       'pruned_percent': 100 * row['pruned'] / row['counts']['input'] if row['counts']['input'] else 0.0})
    need(expected_tree['counted_copies'] == 1920 and not expected_tree['problems'] and levels == expected_tree['levels'],
         'u24 derived funnel differs from the archived result table')
    survivors = {i: sorted(c['keep_lines']) for i, c in main.items() if c['keep_lines']}
    mapping = load(root / 'research/unit-distance-24/survivor-s50/mapping.json')
    need(survivors == {50: [mapping['survivor']]}, 'u24 fleet survivor differs from the checked map')
    for name in ['pilot', 'full', 'phaseb', 'repro']:
        report = load(root / f'research/unit-distance-24/evidence/judge-final-2026-10-07-r2/judge-{name}.json.gz')
        need(report['verdict'] == 'OK' and report['exit'] == 0 and not report['problems'] and not report['pending'] and set(report['accepted_slices']) == assigned[name], 'archived u24 judge report differs from re-judged plan')
    print(f'Portable u24 evidence judge: 1,920 production slices, {len(snapshots)} saved copies; 50 reproduced slices; detail-derived G4, structure, counts, prefix and survivor agree')
    print('Scope: saved known-configuration receipts checked; Engel dataset membership and the original whole-fleet judge are not rerun because that dataset has no redistribution licence.')


def check(order, root):
    root = Path(root)
    sources = load(root / 'EVIDENCE-SOURCES.json')
    public_bindings(root, sources)
    if order == 22:
        original_funnel(root, sources)
        return
    sys.path.insert(0, str(root / 'research/unit-distance-23/tools'))
    aggregate23 = module('aggregate_fleet', root / 'research/unit-distance-23/tools/aggregate_fleet.py')
    if order == 23:
        u23_funnel(root, sources, aggregate23)
    else:
        u24_judge(root, sources, aggregate23)
