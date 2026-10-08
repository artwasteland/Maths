"""Repeat one named enumeration slice, verify its chain, compare frozen graph hashes."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def load(path):
    if not path.exists():
        path = path.with_name(path.name + '.gz')
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as f:
        return json.load(f)


def execute(command, root, log):
    with log.open('w') as output:
        p = subprocess.run(command, cwd=root, stdout=output, stderr=subprocess.STDOUT)
    tail = log.read_text().splitlines()[-6:]
    print('\n'.join(tail))
    if p.returncode:
        raise ValueError('enumeration command failed; exit ' + str(p.returncode))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def check(order, root, index):
    limit = 48 if order == 22 else 1920
    if not 0 <= index < limit:
        raise ValueError('slice outside 0..' + str(limit - 1))
    source = load(root / 'EVIDENCE-SOURCES.json')
    selected = [r for r in source['copies'] if r['slice'] == index and (order != 23 or r['chosen'])]
    if order == 24:
        # The archived judge's chosen production owner defines the comparison copy.
        selected = []
        for name in ['pilot', 'full', 'phaseb']:
            report = load(root / f'research/unit-distance-24/evidence/judge-final-2026-10-07-r2/judge-{name}.json.gz')
            if str(index) in report['cost']['chosen']:
                worker = report['cost']['chosen'][str(index)]['source'].split('/', 1)[0].removeprefix('codex-')
                selected = [r for r in source['copies'] if r['slice'] == index and
                            (r['worker'].removeprefix('codex-') == worker or
                             r['worker'].removeprefix('codex-').startswith(worker + '-'))]
                break
    if not selected:
        raise ValueError('named slice has no frozen comparison copy')
    frozen = root / selected[0]['directory']
    hashes = load(frozen / 'hashes.json')['files']
    ud = root / 'research/unit-distance-22'
    work = root / '.recheck-work'
    # Compile only inside the deposit copy. At most two compiler jobs, already nice 19.
    execute(['make', '-j2', '-C', str(ud / 'enum')], root, work / 'compile-enum.log')
    execute(['make', '-j2', '-C', str(ud / 'filter')], root, work / 'compile-filter.log')
    target = (order, {22: 61, 23: 65, 24: 69}[order])
    level = 13 if order == 22 else 12
    out = work / f's{index}of{limit}'
    command = [sys.executable, '-I', '-B', str(ud / 'enum/run-dag2.py'), '--target-n', str(target[0]), '--target-m', str(target[1]),
               '--output-dir', str(out), '--seed-n', '10', '--jobs', '2', '--shard-size', '10000', '--reach',
               '--prune', '--prune-from', '12', '--prune-filter-only', '--prune-tries', '0', '--prune-max-states', '400',
               '--prune-python', sys.executable, '--slice-level', str(level), '--slice-index', str(index), '--slice-count', str(limit)]
    if order != 22:
        command += ['--forbidden-set', '398', '--verify-stages', '--triangles', '--prune-filter-set', '74',
                    '--ubar', '22=60', '--ubar-justification', load(frozen / 'run-config.json')['ubar_justification']]
    if order == 24:
        command += ['--ubar', '23=64']
    execute(command, root, work / 'enumeration.log')
    checker = ud / 'enum' / ('verify-chain-u24.py' if order == 24 else 'verify-chain.py')
    # The source checker has a historical interpreter default. Change only that
    # orchestration variable in memory, retaining every mathematical check.
    adapter = "import importlib.util,sys;from pathlib import Path;p=Path(sys.argv[1]);s=importlib.util.spec_from_file_location('deposit_chain',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);m.PYTHON=Path(sys.executable);sys.argv=[str(p),*sys.argv[2:]];sys.exit(m.main())"
    execute([sys.executable, '-I', '-B', '-c', adapter, str(checker), str(out), '--check'], root, work / 'chain.log')
    for name, row in hashes.items():
        p = out / name
        if not p.is_file() or digest(p) != row['sha256']:
            raise ValueError('reproduced graph hash differs: ' + name)
        with p.open('rb') as f:
            count = sum(raw.count(b'\n') for raw in iter(lambda: f.read(1048576), b''))
        if count != row['records']:
            raise ValueError('reproduced graph count differs: ' + name)
    derived = root / 'derived'
    derived.mkdir(exist_ok=True)
    (derived / f'slice-{index}-replay.json').write_text(json.dumps({'target': target, 'slice': [level, index, limit],
        'sourceCommit': selected[0]['commit'], 'comparedFiles': len(hashes), 'status': 'PASS'}, indent=2) + '\n')
    print(f'Full named slice s{index}of{limit}: chain checked and {len(hashes)} graph hashes and counts matched')
