"""Independent checker controls and final Round 4 artifact audit."""
import argparse
import ast
from collections import Counter
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
import json
import importlib.metadata
from pathlib import Path
import platform
import sys
from msolve_exact import limits,sha
from exact import verify,graph6,rational,textq
from round2 import write_json
from round4 import HERE,OUT,jsonl
from round3_finish import run_directory


def controls():
    limits();rows=list(jsonl((OUT/'new-records.jsonl').read_bytes()).values())
    embedded=[r for r in rows if r['verdict']=='embedded']
    by_method={}
    for stat in [json.loads(line) for line in (OUT/'stats.jsonl').read_text().splitlines()]:
        if stat.get('method'):by_method.setdefault(stat['method'],stat['g6'])
    chosen=[next(r for r in embedded if r['g6']==c) for c in by_method.values()]
    checks=[]
    for record in chosen:
        verify(record['g6'],record['cert'],max_refinements=256)
        u,v=graph6(record['g6'])[1][0];bad=deepcopy(record)
        bad['cert']['coords'][u][0][0]=textq(rational(bad['cert']['coords'][u][0][0])+1000)
        checks.append({'g6':record['g6'],'expected_local_reason':f'edge:{u},{v}'})
        try:verify(record['g6'],bad['cert'])
        except ValueError as exc:assert str(exc)==checks[-1]['expected_local_reason']
        else:raise AssertionError('mutation:accepted')
        checks[-1]['local_positive_and_red']='PASS'
    import official_check
    green=OUT/'controls/official-green';red=OUT/'controls/official-red'
    run_directory(green,chosen);run_directory(red,[bad]);results=[];oldargv=sys.argv[:]
    try:
        for directory,expected in [(green,'ACCEPT'),(red,'REJECT')]:
            sys.argv=['official_check.py',str(directory),'--output',str(directory/'out')]
            with (directory/'checker.log').open('w') as log,redirect_stdout(log),redirect_stderr(log):official_check.main()
            report=json.loads((directory/'out/report.json').read_text());assert report['status']==expected
            if expected=='REJECT':assert 'edge_equation' in (directory/'out/records.jsonl').read_text()
            results.append({'run':str(directory.relative_to(OUT)),'status':expected,'final_line':(directory/'checker.log').read_text().splitlines()[-1],'seconds':report['elapsed_seconds']})
    finally:sys.argv=oldargv
    write_json(OUT/'controls/official-results.json',{'paired_local':checks,'official':results});print(json.dumps(results,indent=2))


def audit():
    limits();summary=json.loads((OUT/'summary.json').read_text());rows=jsonl((OUT/'merged-records.jsonl').read_bytes())
    own=jsonl((OUT/'new-records.jsonl').read_bytes())
    assert sha((OUT/'new-records.jsonl').read_bytes())==summary['new_records_sha256']
    assert jsonl((OUT/'search/records.jsonl').read_bytes())==own
    assert len(rows)==1515 and len(own)==summary['search_count']
    assert dict(Counter(r['verdict'] for r in rows.values()))==summary['merged_counts']
    unknown=''.join(c+'\n' for c in sorted(rows) if rows[c]['verdict']=='unknown')
    assert (OUT/'UNDECIDED.g6').read_text()==(OUT/'run/UNKNOWN.g6').read_text()==unknown
    checker=json.loads((OUT/'run/out/report.json').read_text());final=(OUT/'run/checker.log').read_text().splitlines()[-1]
    assert checker['status']=='ACCEPT' and final=='ACCEPT run verified'
    assert checker['counts']==dict(summary['merged_counts']) and checker['input_count']==1515
    assert checker['input_sha256']==sha((OUT/'run/input.g6').read_bytes())
    merged=OUT/'merged-records.jsonl';assert sha(merged.read_bytes())==summary['merged_sha256']
    assert any(Path(r['path']).resolve()==merged.resolve() and r['sha256']==summary['merged_sha256'] for r in checker['files'])
    assert checker['checker_sha256']==sha((HERE.parent/'check/gp10check.py').read_bytes())
    source_names=['generic_exact.py','rigid_system.py','round2.py','round3.py','round4.py','round4_selftest.py','round4_entry_controls.py','round4_finish.py','gp_field.py','official_check.py','msolve_exact.py','round2_phase.py']
    for name in source_names:ast.parse((HERE/name).read_text());assert chr(8212) not in (HERE/name).read_text()
    for label in ('start','end'):
        meta=json.loads((OUT/'snapshots'/label/'snapshot.json').read_text())
        for name,row in meta['files'].items():assert sha((OUT/'snapshots'/label/name).read_bytes())==row['sha256']
    assert summary['end']['emb_complete']
    triage=(OUT/'rigid-no-embedding.g6').read_text().splitlines()
    assert len(triage)==len(set(triage))==summary['rigid_triage']
    assert all(rows[c]['verdict']=='unknown' for c in triage)
    assert all(rows[c]==r for c,r in own.items() if r['verdict']=='embedded')
    controls=json.loads((OUT/'controls/results.json').read_text());official=json.loads((OUT/'controls/official-results.json').read_text())
    assert all(c['status']=='PASS' for c in controls['checks'])
    assert [r['status'] for r in official['official']]==['ACCEPT','REJECT']
    stats=[json.loads(line) for line in (OUT/'stats.jsonl').read_text().splitlines()]
    frames=Counter();attempt_reasons=Counter();attempt_count=0;all_three=0;all_six=0
    for row in stats:
        for stage in row['stages']:
            assert stage['wall_seconds']<stage['cap_seconds']+1
            if 'attempts' in stage:
                tries=stage['attempts'];attempt_count+=len(tries)
                all_three+=len({tuple(a['frame']) for a in tries})==3
                all_six+=len(tries)==6
                for a in tries:attempt_reasons[a.get('reason','none').split('{')[0]]+=1
    result={'status':'PASS','scope':'1515 supplied candidates, sample profile, no minimality derivation',
        'checker_final_line':final,'checker_seconds':checker['elapsed_seconds'],'checker_counts':checker['counts'],
        'checker_sha256':checker['checker_sha256'],'new_records_sha256':summary['new_records_sha256'],'merged_sha256':summary['merged_sha256'],'summary_sha256':sha((OUT/'summary.json').read_bytes()),
        'sources':{name:sha((HERE/name).read_bytes()) for name in source_names},'python':platform.python_version(),
        'versions':{name:importlib.metadata.version(name) for name in ['sympy','python-flint','numpy','scipy','pynauty']},
        'entry_controls':json.loads((OUT/'controls/entry/results.json').read_text()),
        'SYMPY_GROUND_TYPES':'python','local_controls':controls['passed'],'legacy_controls':controls['legacy_passed'],
        'msolve_attempts':attempt_count,'msolve_graphs_trying_three_frames':all_three,'msolve_graphs_trying_six_variants':all_six,
        'msolve_attempt_reasons':dict(attempt_reasons),'max_new_record_bytes':max(len(json.dumps(r).encode()) for r in own.values())}
    result['numeric_rejection_example']=next({'g6':r['g6'],'frame':a['frame'],'variant':a['variant'],'reason':a['reason']} for r in stats for stage in r['stages'] for a in stage.get('attempts',[]) if 'pinning:no_distinct_numeric_embedding' in a.get('reason',''))
    write_json(OUT/'audit.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['controls','audit']);a=p.parse_args()
    controls() if a.command=='controls' else audit()
