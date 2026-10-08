#!/usr/bin/env python3
"""survey11.py: stream a GP-11 records.jsonl once and describe its refuted certificates.

Usage:
    python survey11.py RECORDS.jsonl SURVEY.json [INDEX.jsonl]

Reads the file as data only, one line at a time (some lines are 8 MiB).  Every line's verdict is
classified from its JSON; refuted lines are parsed in full and described (certificate type and
the sub-features that decide which verifier branch is needed).  The optional INDEX.jsonl gets one
line per refuted record: {"i", "line", "offset", "length", "g6", "type"}, which
verify_refutations11.py can use to seek straight to the refuted records.
"""
import json
import sys
import time
import hashlib
from collections import Counter

TAILS = {b'"verdict":"embedded"}': 'embedded', b'"verdict":"refuted"}': 'refuted',
         b'"verdict":"unknown"}': 'unknown'}


def walk_tree(node):
    stack = [node]
    while stack:
        nd = stack.pop()
        yield nd
        stack.extend(nd.get('children', []))


def describe(cert):
    """Feature tags of one refuted certificate (for the survey only; no checking here)."""
    t = cert.get('type')
    tags = {'type': t, 'keys': ','.join(sorted(cert.keys()))}
    if t == 'tu':
        st = cert.get('steps', [])
        tags['steps'] = len(st)
        tags['gadgets'] = '-'.join(str(s.get('gadget')) for s in st)
        end = cert.get('end', {})
        if 'forbidden' in end:
            tags['end'] = 'forbidden'
            tags['end_index'] = end['forbidden']
        elif 'refuted' in end:
            tags['end'] = 'refuted'
            tags['end_g6'] = end['refuted']
        else:
            tags['end'] = 'other:' + ','.join(sorted(end))
    elif t == 'sub':
        tags['sub_index'] = cert.get('index')
        tags['sub_g6'] = cert.get('g6')
    elif t in ('null', 'real', 'null-dag', 'real-dag'):
        tags['sat'] = len(cert.get('sat', []))
        if 'rows' in cert:
            tags['rows'] = len(cert['rows'])
        if 'cofactors' in cert:
            tags['cofactors'] = len(cert['cofactors'])
        if t.startswith('real'):
            tags['proof'] = 'sturm' if 'sturm' in cert else ('sos' if 'sos' in cert else 'none')
        tags['system'] = 'system' in cert
    elif t == 'tree':
        w = cert.get('witness', {})
        f = w.get('field', {})
        tags['field_degree'] = len(f.get('minpoly', [])) - 1
        tags['minpoly'] = json.dumps(f.get('minpoly'))
        nodes = 0
        moves = Counter()
        for nd in walk_tree(w.get('tree', {})):
            nodes += 1
            moves[nd.get('move', {}).get('kind')] += 1
        tags['nodes'] = nodes
        tags['moves'] = dict(moves)
    return tags


def main(argv):
    src, dst = argv[1], argv[2]
    idx_path = argv[3] if len(argv) > 3 else None
    t0 = time.time()
    verdicts = Counter()
    emb_types = Counter()
    anomalies = []
    types = Counter()
    sub = Counter()
    largest = []
    g6_seen = {}
    dup = []
    refuted = []
    sha = hashlib.sha256()
    offset = 0
    idx_out = open(idx_path, 'w') if idx_path else None
    with open(src, 'rb', buffering=1 << 22) as fh:
        for lineno, line in enumerate(fh, 1):
            sha.update(line)
            length = len(line)
            body = line[:-1] if line.endswith(b'\n') else line
            if not line.endswith(b'\n'):
                anomalies.append({'line': lineno, 'what': 'no trailing newline'})
            verdict = None
            for tail, v in TAILS.items():
                if body.endswith(tail):
                    verdict = v
                    break
            rec = None
            if verdict is None or verdict == 'refuted':
                try:
                    rec = json.loads(body)
                except Exception as exc:
                    anomalies.append({'line': lineno, 'what': 'json: %s' % str(exc)[:80]})
                    offset += length
                    continue
                v2 = rec.get('verdict')
                if verdict is None:
                    anomalies.append({'line': lineno, 'what': 'other key order (verdict not last); verdict %r' % (v2,)})
                    verdict = v2
                elif v2 != verdict:
                    anomalies.append({'line': lineno, 'what': 'tail says %s, JSON says %r' % (verdict, v2)})
                    verdict = v2
            verdicts[verdict] += 1
            # the g6 of every record (for duplicate detection); cheap extraction from the tail
            if rec is not None:
                g6 = rec.get('g6')
                if verdict == 'embedded' and isinstance(rec.get('cert'), dict):
                    emb_types[str(rec['cert'].get('type'))] += 1
            else:
                # sorted-key compact line: the record's g6 is the LAST "g6" key.  graph6 may
                # contain a backslash, which JSON escapes, so unescape with the JSON decoder.
                k = body.rfind(b'"g6":"')
                if k >= 0:
                    e = k + 6
                    while body[e] != 34:          # closing quote; skip escaped characters
                        e += 2 if body[e] == 92 else 1
                    g6 = json.loads(body[k + 5:e + 1])
                else:
                    g6 = None
                if verdict == 'embedded':
                    j = body.find(b'"type":"', max(0, k - 40))
                    if j >= 0:
                        emb_types[body[j + 8:body.index(b'"', j + 8)].decode()] += 1
            if g6 in g6_seen:
                dup.append({'g6': g6, 'lines': [g6_seen[g6], lineno]})
            else:
                g6_seen[g6] = lineno
            if verdict == 'refuted':
                cert = rec.get('cert', {})
                tags = describe(cert)
                types[tags['type']] += 1
                for key in ('end', 'proof', 'field_degree', 'steps', 'gadgets', 'sub_index'):
                    if key in tags:
                        sub['%s %s=%s' % (tags['type'], key, tags[key])] += 1
                if tags.get('end') == 'forbidden':
                    sub['tu end_index=%s' % tags['end_index']] += 1
                ent = {'line': lineno, 'offset': offset, 'length': length, 'g6': rec.get('g6'),
                       'tags': tags}
                refuted.append(ent)
                if idx_out is not None:
                    idx_out.write(json.dumps({'i': len(refuted) - 1, 'line': lineno, 'offset': offset,
                                              'length': length, 'g6': rec.get('g6'),
                                              'type': tags['type']}) + '\n')
                del rec, cert
            offset += length
            if lineno % 50000 == 0:
                sys.stderr.write('%d lines, %.1f GB, %.0fs, refuted %d\n' % (
                    lineno, offset / 1e9, time.time() - t0, len(refuted)))
    if idx_out is not None:
        idx_out.close()
    refuted_sorted = sorted(refuted, key=lambda e: -e['length'])
    by_type_size = {}
    for e in refuted:
        t = e['tags']['type']
        s = by_type_size.setdefault(t, {'n': 0, 'bytes': 0, 'max': 0})
        s['n'] += 1
        s['bytes'] += e['length']
        s['max'] = max(s['max'], e['length'])
    tree_nodes = Counter()
    rows = Counter()
    moves = Counter()
    for e in refuted:
        tg = e['tags']
        if 'nodes' in tg:
            tree_nodes[tg['nodes']] += 1
            for k, v in tg['moves'].items():
                moves[k] += v
        if 'rows' in tg:
            rows[tg['rows']] += 1
    targets = Counter()
    for e in refuted:
        tg = e['tags']
        if tg.get('end') == 'refuted':
            targets['tu->refuted'] += 1
        if tg['type'] == 'sub':
            targets['sub index=%s' % ('none' if tg.get('sub_index') is None else 'given')] += 1
    out = {
        'file': src,
        'file_sha256': sha.hexdigest(),
        'bytes': offset,
        'lines': sum(verdicts.values()),
        'verdicts': dict(verdicts),
        'embedded_types': dict(emb_types),
        'duplicate_g6': dup[:50],
        'duplicate_g6_count': len(dup),
        'anomalies': anomalies[:50],
        'anomaly_count': len(anomalies),
        'anomaly_kinds': dict(Counter(a['what'].split(';')[0] for a in anomalies)),
        'refuted_types': dict(types),
        'refuted_subfeatures': dict(sorted(sub.items())),
        'refuted_bytes_by_type': by_type_size,
        'tree_node_histogram': dict(sorted(tree_nodes.items())),
        'tree_moves': dict(moves),
        'dag_row_histogram': dict(sorted(rows.items())),
        'pointer_kinds': dict(targets),
        'largest_20': [{'line': e['line'], 'g6': e['g6'], 'type': e['tags']['type'],
                        'bytes': e['length']} for e in refuted_sorted[:20]],
        'seconds': round(time.time() - t0, 1),
    }
    with open(dst, 'w') as fo:
        json.dump(out, fo, indent=1)
    print(json.dumps({k: out[k] for k in ('lines', 'verdicts', 'embedded_types', 'duplicate_g6_count',
                                          'anomaly_count', 'refuted_types', 'pointer_kinds', 'seconds')}))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
