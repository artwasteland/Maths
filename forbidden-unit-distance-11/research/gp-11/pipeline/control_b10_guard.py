"""Fail closed at the producer's answer boundary, before importing search code."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
GP10 = ROOT / 'research/gp-10'
GP11 = ROOT / 'research/gp-11'
DATA = ROOT / 'research/unit-distance-22/data'
B10 = GP10 / 'data/B10.g6'
B10_SHA = '3cec678af7e0f2dec59b5f362e6d18e3fcb993ee94b701a8da8280529bd1321f'
F9_SHA = 'ff1badd63a155fe71e53e2fef54888425f47bcae1a9e7b1d43e0df04cfff3c1a'


class Refused(BaseException):
    """Cannot be swallowed by the producers' ordinary search-error handlers."""


def refuse(rule, detail, started=False):
    raise Refused(f'REFUSED leak_guard:{rule} {detail}; search_started={str(started).lower()}')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def order(code):
    if not isinstance(code, str) or not code or not 63 <= ord(code[0]) < 126:
        refuse('graph6', 'invalid short graph6')
    return ord(code[0]) - 63


def scan(value, where):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ('g6', 'refuted') and isinstance(child, str) and order(child) > 9:
                refuse('answer_order', f'{where} order={order(child)} maximum=9')
            if key == 'coords' and isinstance(child, list) and len(child) > 9:
                refuse('answer_order', f'{where} coordinates={len(child)} maximum=9')
            scan(child, where)
    elif isinstance(value, list):
        for child in value:
            scan(child, where)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            refuse('duplicate_json_key', key)
        result[key] = value
    return result


def bases(paths):
    """Validate every byte before exposing even the first lower-order row."""
    records = {}
    receipts = {}
    for source in paths:
        source = Path(source).resolve()
        # Historical result trees and indexes are not eligible even if filtered.
        forbidden = (GP10 / 'cloud', GP11 / 'embed', GP11 / 'pipeline/results',
                     GP11 / 'check/results', DATA / 'forbidden-398.json',
                     GP10 / 'embed/host_sources.json', GP10 / 'embed/host_certificates.json')
        if source.is_dir() or any(source.is_relative_to(p) for p in forbidden):
            refuse('answer_source', str(source))
        if source.stat().st_size > 32 * 1024 * 1024:
            refuse('source_size', str(source))
        opener = gzip.open if source.suffix == '.gz' else open
        total = 0
        with opener(source, 'rt') as stream:
            number = 0
            while line := stream.readline(8 * 1024 * 1024 + 1):
                number += 1
                total += len(line)
                if len(line) > 8 * 1024 * 1024 or total > 64 * 1024 * 1024:
                    refuse('source_size', str(source))
                row = json.loads(line, object_pairs_hook=unique_object)
                scan(row, f'{source.name}:{number}')
                if set(row) != {'g6', 'verdict', 'cert'} or row['verdict'] != 'embedded' or row['cert'].get('type') != 'exact':
                    refuse('base_schema', f'{source.name}:{number} requires direct exact embedding')
                if not 2 <= order(row['g6']) <= 9:
                    refuse('answer_order', f'{source.name}:{number}')
                if row['g6'] in records and records[row['g6']] != row:
                    refuse('duplicate_base', row['g6'])
                records[row['g6']] = row
        receipts[str(source)] = sha(source)
    return records, receipts


def sources():
    """Explicit code surface. No historical evidence, hosts, F10 or indexes."""
    paths = []
    for folder in (GP11 / 'pipeline', GP11 / 'embed', GP10 / 'embed', GP10 / 'refute',
                   GP10 / 'drive', GP10 / 'check', ROOT / 'research/unit-distance-22/filter'):
        paths.extend(p for p in folder.iterdir() if p.suffix in ('.py', '.c', '.h', '.gp') and not p.name.startswith('test_'))
    paths += [ROOT / 'research/unit-distance-22/check/udcheck.py', DATA / 'forbidden-74.json',
              DATA / 'forbidden-74.g6', DATA / 'tu-gadgets.json', B10]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def install_read_guard(allowed, state, output):
    """Audit Python reads of repository data and prior /tmp job data.

    This is an accidental-leak guard for reviewed code, not an OS security sandbox.
    CAS children receive only freshly written systems and no answer paths.
    """
    allowed = {str(Path(p).resolve()) for p in allowed}
    state = Path(state).resolve()
    output = Path(output).resolve()
    opened = set()

    def audit(event, args):
        if event != 'open' or not isinstance(args[0], (str, bytes)):
            return
        path = Path(os.fsdecode(args[0])).resolve()
        mode, flags = args[1:3]
        # shutil.rmtree opens child directories relative to a directory fd.
        # The audit event omits that fd. These nonblocking directory opens do
        # not read certificate contents and must not be resolved against cwd.
        if mode is None and flags & os.O_NONBLOCK:
            return
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR))
        if writing or path.is_relative_to(state) or path.is_relative_to(output):
            return
        if str(path) in allowed:
            opened.add(str(path))
            return
        if path.is_relative_to(ROOT) or path.is_relative_to('/tmp'):
            # Interpreter bytecode probes are harmless; source execution is pinned.
            if path.suffix == '.pyc' and '__pycache__' in path.parts:
                return
            refuse('runtime_read', str(path), started=True)
    sys.addaudithook(audit)
    return opened
