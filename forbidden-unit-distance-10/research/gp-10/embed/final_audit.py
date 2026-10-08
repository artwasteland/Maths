"""Audit measured artifacts, canonical labels, controls and module hygiene."""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
from collections import Counter
from gp10embed import limits
from exact import verify,graph6
from measure import HERE,RESULTS,SAMPLES,read_records,stages,canonical,audit,write_json

def main():
    limits();start=time.monotonic();audit()
    import sympy,flint,numpy,scipy,networkx
    canonical_counts={};method_counts={};host_counts=Counter();reasons=Counter();numeric_converged=[]
    for sample in SAMPLES:
        codes=(RESULTS/sample/'input.g6').read_text().splitlines()
        assert canonical(codes)==codes,('noncanonical input',sample)
        canonical_counts[sample]=len(codes)
        for p in stages(sample):
            label=p.name[:-len('.meta.json')]
            records=read_records(p.with_name(label+'.records.jsonl'))
            stats=read_records(p.with_name(label+'.stats.jsonl'))
            assert [r['g6'] for r in records]==[s['g6'] for s in stats]
            for r,s in zip(records,stats):
                assert r['verdict']==s['verdict']
                json.dumps(r,allow_nan=False);json.dumps(s,allow_nan=False)
                if r['verdict']=='embedded':verify(r['g6'],r['cert'])
                for a in s['budget']['attempts']:
                    if a['method']=='host' and r['verdict']=='embedded':host_counts[a['host']]+=1
                    if a['method']=='numeric':
                        reasons[a['reason']]+=1
                        if a.get('residual',1)>1e-12:continue
                        numeric_converged.append({'sample':sample,'g6':r['g6'],'residual':a['residual'],'reason':a['reason'],'verdict':r['verdict']})
            meta=json.loads(p.read_text())
            assert len(records)==meta['attempted']
            assert dict(Counter(r['verdict'] for r in records))==meta['counts']
            method_counts[sample+'/'+label]=len(records)
    labels=json.loads((RESULTS/'B9p'/'labels.json').read_text())
    bad=[r['g6'] for r in read_records(RESULTS/'B9p'/'records.jsonl') if r['verdict']=='embedded' and labels[r['g6']]=='forbidden']
    assert not bad
    names=json.loads((RESULTS/'named'/'names.json').read_text())
    verdicts={r['g6']:r['verdict'] for r in read_records(RESULTS/'named'/'records.jsonl')}
    positives=('Petersen','Golomb','pentagonal_prism','extremal_10','Moser_spindle')
    for name in positives:
        assert verdicts[names[name]]=='embedded'
        witnesses=[]
        for p in stages('named'):
            meta=json.loads(p.read_text())
            if meta['method']=='host':continue
            label=meta['label']
            witnesses.extend(r for r in read_records(p.with_name(label+'.records.jsonl')) if r['g6']==names[name] and r['verdict']=='embedded')
        assert witnesses,('no general-search witness',name)
    for name,c in names.items():
        if name not in positives:assert verdicts[c]=='unknown'
    files=list(HERE.rglob('*'));source_hashes={};em_dash=[]
    for p in files:
        if p.is_file():
            raw=p.read_bytes()
            if b'\xe2\x80\x94' in raw:em_dash.append(str(p.relative_to(HERE)))
            if p.suffix=='.py':
                ast.parse(raw,filename=str(p));source_hashes[p.name]=hashlib.sha256(raw).hexdigest()
    assert not em_dash,em_dash
    environment={'python':sys.version.split()[0],'executable':sys.executable,'sympy':sympy.__version__,
                 'flint':flint.__version__,'numpy':numpy.__version__,'scipy':scipy.__version__,
                 'networkx':networkx.__version__,'SYMPY_GROUND_TYPES':os.environ['SYMPY_GROUND_TYPES'],
                 'niceness':os.getpriority(os.PRIO_PROCESS,0),'virtual_memory_limit_bytes':resource.getrlimit(resource.RLIMIT_AS)[0]}
    result={'environment':environment,'canonical_inputs':canonical_counts,'method_record_counts':method_counts,
            'host_hits_by_source':dict(host_counts),'numeric_attempt_reasons':dict(reasons),
            'numeric_converged_and_refused':numeric_converged,'forbidden_accepted':len(bad),
            'named_positive_general_search':'passed','negative_embedder_controls':'unknown',
            'python_sources':source_hashes,'em_dash_files':em_dash,'seconds':time.monotonic()-start}
    write_json(RESULTS/'final-audit.json',result)
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
