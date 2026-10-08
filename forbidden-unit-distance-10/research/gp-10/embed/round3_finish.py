"""Assemble, independently check, and report the round-three host results."""
import argparse
from collections import Counter
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
import shutil
import subprocess
from msolve_exact import limits,sha,Poly
from exact import verify,CertificateError,rational,textq,graph6,adjacency
from hosts import check_mapping,database
from gp_field import convert
from round2 import write_json,task_id
from round3 import OUT,HERE


def jsonl(path):return [json.loads(line) for line in path.read_text().splitlines()]

def save_rows(path,rows):path.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def run_directory(directory,rows,relative_records='records.jsonl'):
    directory.mkdir(parents=True,exist_ok=True)
    rows=sorted(rows,key=lambda r:r['g6']);text=''.join(r['g6']+'\n' for r in rows)
    (directory/'input.g6').write_text(text)
    (directory/'UNKNOWN.g6').write_text(''.join(r['g6']+'\n' for r in rows if r['verdict']=='unknown'))
    if relative_records=='records.jsonl':save_rows(directory/'records.jsonl',rows)
    write_json(directory/'run.json',{'profile':'sample','input':'input.g6','input_sha256':sha(text.encode()),
        'records':[relative_records],'unknown':'UNKNOWN.g6','derive':False})


def collect():
    limits();codes=(OUT/'gaps-input.g6').read_text().splitlines();assert len(codes)==len(set(codes))==13
    assert sha((OUT/'gaps-input.g6').read_bytes())==sha((HERE/'results/B9-GAPS-13.g6').read_bytes())
    gaps=[json.loads((OUT/'gaps13'/task_id(c)/'record.json').read_text()) for c in codes]
    stats=[json.loads((OUT/'gaps13'/task_id(c)/'stats.json').read_text()) for c in codes]
    assert all(r['verdict']=='embedded' for r in gaps)
    special=[json.loads((OUT/name/'record.json').read_text()) for name in ('H1','H2')]
    old=jsonl(HERE/'results/round2/union-records.jsonl');merged={r['g6']:r for r in old};before=dict(merged)
    for record in gaps+special:
        verify(record['g6'],record['cert'],max_refinements=256);merged[record['g6']]=record
    assert len(merged)==len(old)==6078
    new=sorted(c for c,r in merged.items() if r['verdict']=='embedded' and before[c]['verdict']!='embedded')
    assert new==sorted(codes)
    rows=[merged[c] for c in sorted(merged)]
    save_rows(OUT/'gaps-records.jsonl',gaps);save_rows(OUT/'special-host-records.jsonl',special)
    save_rows(OUT/'records.jsonl',gaps+special);save_rows(OUT/'union-records.jsonl',rows);save_rows(OUT/'stats.jsonl',stats)
    (OUT/'new-embedded.g6').write_text(''.join(c+'\n' for c in new))
    (OUT/'gaps13/UNKNOWN.g6').write_text('');save_rows(OUT/'gaps13/records.jsonl',gaps)
    (OUT/'UNKNOWN.g6').write_text(''.join(r['g6']+'\n' for r in rows if r['verdict']=='unknown'))
    run_directory(OUT/'run',rows,'../union-records.jsonl')
    counts=dict(Counter(r['verdict'] for r in rows))
    summary={'gaps_requested':13,'gaps_embedded':13,'gaps_unknown':0,'method':'G118_per_map',
        'union_counts':counts,'union_records':len(rows),'new_unique_embeddings':len(new),
        'degree_distribution':dict(Counter(s['degree'] for s in stats)),
        'gap_wall_seconds_sum':sum(s['wall_seconds'] for s in stats),
        'gap_pari_seconds_sum':sum(s['pari_seconds'] for s in stats),
        'batch':json.loads((OUT/'batches/gaps13-0-13.json').read_text()),
        'special_hosts':{name:json.loads((OUT/name/'result.json').read_text()) for name in ('H1','H2')},
        'special_hosts_already_embedded':all(before[r['g6']]['verdict']=='embedded' for r in special),
        'optional':json.loads((OUT/'optional-decision.json').read_text()),
        'union_sha256':sha((OUT/'union-records.jsonl').read_bytes())}
    write_json(OUT/'summary.json',summary);print(json.dumps(summary,indent=2))


def controls():
    limits();rows=jsonl(OUT/'records.jsonl');checks=[]
    for record in rows:
        code=record['g6'];cert=verify(code,record['cert'],max_refinements=256)
        bad=deepcopy(cert);bad['coords'][0][0][0]=textq(rational(bad['coords'][0][0][0])+1000)
        n,edges=graph6(code);edge=next(e for e in edges if 0 in e);expected=f'edge:{edge[0]},{edge[1]}'
        try:verify(code,bad)
        except CertificateError as exc:reason=str(exc);assert reason==expected,(code,reason,expected)
        else:raise AssertionError('coordinate mutation accepted')
        checks.append({'g6':code,'positive':'PASS','red':'PASS','reason':reason})
    # Repeat an actual degree-16 image, including its graph-derived PARI seed.
    code='H?DTJQx';directory=OUT/'gaps13'/task_id(code)
    proposal=json.loads((directory/'proposal.json').read_text());original=json.loads((directory/'record.json').read_text())
    repeated,call=convert(proposal['expressions'],OUT/'controls/degree16-repeat',180,g6=code)
    assert repeated==original['cert']
    assert call['output_sha256']==json.loads((directory/'field-call.json').read_text())['output_sha256']
    write_json(OUT/'controls/local-results.json',{'checks':checks,'degree16_repeat':'PASS','repeat_seconds':call['seconds']})
    import official_check
    green=OUT/'controls/official-green';red=OUT/'controls/official-red'
    run_directory(green,rows)
    bad=deepcopy(rows[0]);bad['cert']['coords'][0][0][0]=textq(rational(bad['cert']['coords'][0][0][0])+1000)
    run_directory(red,[bad]);results=[]
    oldargv=sys.argv[:]
    try:
        for directory,expected in [(green,'ACCEPT'),(red,'REJECT')]:
            sys.argv=['official_check.py',str(directory),'--output',str(directory/'out')]
            with (directory/'checker.log').open('w') as log,redirect_stdout(log),redirect_stderr(log):
                result=official_check.main()
            report=json.loads((directory/'out/report.json').read_text());assert report['status']==expected
            final=(directory/'checker.log').read_text().splitlines()[-1]
            if expected=='REJECT':assert 'edge_equation' in (directory/'out/records.jsonl').read_text()
            results.append({'run':str(directory.relative_to(OUT)),'status':expected,'final_line':final,'seconds':report['elapsed_seconds']})
    finally:sys.argv=oldargv
    write_json(OUT/'controls/official-results.json',results);print(json.dumps({'local_paired_controls':len(checks),'official':results},indent=2))


def finish():
    limits();summary=json.loads((OUT/'summary.json').read_text());checker=json.loads((OUT/'run/out/report.json').read_text())
    final=(OUT/'run/checker.log').read_text().splitlines()[-1]
    assert checker['status']=='ACCEPT' and final=='ACCEPT run verified'
    assert checker['counts']==dict(summary['union_counts'],refuted=0)
    assert checker['input_count']==6078 and checker['input_sha256']==sha((OUT/'run/input.g6').read_bytes())
    union=OUT/'union-records.jsonl';assert sha(union.read_bytes())==summary['union_sha256']
    assert any(Path(row['path']).resolve()==union.resolve() and row['sha256']==summary['union_sha256'] for row in checker['files'])
    assert checker['checker_sha256']==sha((HERE.parent/'check/gp10check.py').read_bytes())
    rows=jsonl(union);assert len(rows)==len({r['g6'] for r in rows})==6078
    assert (OUT/'UNKNOWN.g6').read_text()==(OUT/'run/UNKNOWN.g6').read_text()==''.join(r['g6']+'\n' for r in rows if r['verdict']=='unknown')
    local=json.loads((OUT/'controls/local-results.json').read_text());official=json.loads((OUT/'controls/official-results.json').read_text())
    assert len(local['checks'])==15 and all(r['positive']==r['red']=='PASS' for r in local['checks'])
    assert [r['status'] for r in official]==['ACCEPT','REJECT']
    special_maps=json.loads((OUT/'special-host-maps.json').read_text())
    assert len(special_maps)==26 and all(r['map'] is None and r['nodes']<=100000 for r in special_maps)
    host=database()['G118'];stats=jsonl(OUT/'stats.jsonl')
    for row in stats:
        code=row['g6'];directory=OUT/'gaps13'/task_id(code);call=json.loads((directory/'field-call.json').read_text())
        n,edges=graph6(code);check_mapping(adjacency(n,edges),host['adj'],row['map'])
        assert call['seed']==int(sha(code.encode())[:16],16) and call['threads']==1
        assert call['input_sha256']==sha((directory/'field.gp').read_bytes())
        assert call['output_sha256']==sha((directory/'field.log').read_bytes())
        assert not call['timeout'] and call['returncode']==0 and (directory/'field.log').read_text().splitlines()[-1]=='GP_FIELD_OK'
    for path,expected in json.loads((OUT/'sources.json').read_text()).items():assert sha(Path(path).read_bytes())==expected
    for record in jsonl(OUT/'records.jsonl'):
        factors=Poly(record['cert']['field']['minpoly']).factor()[1]
        assert len(factors)==1 and factors[0][1]==1
    for name in ('H1','H2'):
        result=summary['special_hosts'][name]
        assert result['control_positive']=='PASS' and result['table_polynomials_verified']==9
        assert result['table_red']=='table:minpoly:0'
    gp_path=Path(shutil.which('gp')).resolve()
    gp_version=subprocess.run([str(gp_path),'-fq'],input='default(nbthreads,1);print(version());quit;\n',text=True,capture_output=True,timeout=10,check=True).stdout.strip()
    source_names=['gp_field.py','gp_special.py','round3.py','round3_finish.py','official_check.py','exact.py','hosts.py','msolve_exact.py','round2_phase.py','round2.py']
    audit={'status':'PASS','gaps_closed':13,'new_unique_embeddings':13,'union_counts':checker['counts'],'paired_new_record_controls':15,
        'official_final_line':final,'union_sha256':summary['union_sha256'],
        'code_sha256':{name:sha((HERE/name).read_bytes()) for name in source_names},
        'maximum_record_bytes':max(len(json.dumps(r).encode()) for r in rows),'optional_status':summary['optional']['status'],
        'new_fields_irreducible':15,'pari':{'path':str(gp_path),'sha256':sha(gp_path.read_bytes()),'version':gp_version}}
    assert audit['maximum_record_bytes']<8*1024*1024
    write_json(OUT/'final-audit.json',audit)
    text=(HERE/'REPORT.md').read_text().split('\n## Round 3\n',1)[0]
    text=text.replace('\n## UNCERTAIN\n','\n## Round 2 limitations (historical)\n\nThe following limitations describe round two. Round-three results follow.\n')
    q=summary['optional']['checks'][-1]
    body=['## Round 3\n',
        'All 13 supplied nine-vertex gaps now have exact embeddings. Each closed by a map into G118 followed by conversion of only its image coordinates. No gap required H1 or H2. No refutation is emitted.\n',
        f'The new union contains {checker["counts"]["embedded"]:,} embedded and {checker["counts"]["unknown"]:,} unknown records out of 6,078, with 13 new unique embeddings. The official checker took {checker["elapsed_seconds"]:.3f} seconds and ended with exactly:\n\n```text\n'+final+'\n```\n',
        '| Input g6 | Closing method | Real field degree | Graph wall time (s) |\n|---|---|---:|---:|']
    for row in stats:body.append('| `'+row['g6'].replace('|','\\|')+'` | G118 image field | '+str(row['degree'])+' | '+f'{row["wall_seconds"]:.3f}'+' |')
    body += [f'\nThe stated 13-graph production sample took {summary["batch"]["wall_seconds"]:.3f} seconds as a batch. Summed graph time was {summary["gap_wall_seconds_sum"]:.3f} seconds, including {summary["gap_pari_seconds_sum"]:.3f} seconds in PARI. These exclude development, the preserved pilot pass and the independent checker. Mapping has a 60-second watchdog and a 10,000,000-node cap; PARI has 180 seconds per image.\n',
        'Numerical adjacency proposes injective maps. PARI evaluates only the mapped radical expressions, adjoining square roots when necessary and reducing the field. It then chooses a linear combination of image coordinates and solves exact rational linear systems to express every coordinate in its powers. Because that primitive element is itself a combination of the coordinates, these two inclusions establish equality with the field generated by the image coordinates. Root selection is numerical; acceptance still requires exact edge reduction, sign change and certified distinctness in the existing verifier.\n',
        'The first PARI probe reached degree 8 but timed out at 180 seconds during matrix conversion, with thread-stack allocation warnings under the address-space cap. Setting `default(nbthreads,1)` resolved this in the repeat. Both attempts are retained. The final implementation seeds PARI from the canonical graph hash, and its degree-16 production image repeated byte-for-byte.\n',
        '| Exceptional host | Canonical g6 | Real field degree | Construction time (s) | Printed polynomials checked |\n|---|---|---:|---:|---:|']
    for name,row in summary['special_hosts'].items():body.append(f'| {name} | ``{row["g6"]}`` | {row["degree"]} | {row["seconds"]:.3f} | {row["table_polynomials_verified"]} |')
    body += ['\nH1 and H2 were reconstructed from the paper\'s fixed coordinates and equilateral-triangle relations in `uglyFigure`, with the remaining equations solved by msolve. Every printed polynomial in z=x+iy was then checked exactly in the resulting real field. Their canonical graphs were already embedded in round two; the new union replaces those two certificates with these table-validated ones so the official checker checks them too. All 26 graph-host pairs were searched for a subgraph map, with no hits.\n',
        'To match H2\'s figure, the last two table rows are interpreted as displacement coordinates from (sqrt(3),0). Adding sqrt(3) to their x coordinates agrees with the figure and is necessary for its edge set. The implementation validates their printed polynomials before that translation. Rounded coordinates only select branches; they are not proof data. The source file and notebook hashes, printed coefficients, formulas, solver inputs and exact certificates are retained. No network fetch was needed.\n',
        f'The optional pass on 990 maximal and 41 uniform unknowns was deferred: one-minute load was {q["load_average"][0]:.3f}, two-second CPU idle fraction {q["cpu_idle_fraction_2s"]:.3f}, and available memory {q["available_memory_kib"]:,} KiB. The pre-existing quiet criteria require load at most 2.0, idle fraction at least 0.5, and available memory at least 1,572,864 KiB. Both load and idle failed. Zero optional inputs were attempted; their round-two records remain in the union.\n',
        'Validation passed 15 paired positive/one-coordinate mutation checks on the 13 gaps and two exceptional hosts. Each mutation failed on the expected edge. Two PARI fixtures also passed positive, mutation and deterministic-repeat checks; H1 and H2 each rejected a one-coefficient printed-polynomial mutation with `table:minpoly:0`. The official checker accepted the 15-record control and rejected its one-coordinate mutation with `edge_equation`, then accepted the complete merged union.\n',
        'Commands and limits are recorded in [ROUND3.md](ROUND3.md). Computational commands used the frozen Python, `-B`, niceness 15 and `ulimit -v 1000000`, with at most one child. PARI and msolve use one thread. The unchanged official checker increases its niceness to 19. The existing wrapper redirects its scratch directory into `/tmp/gp10-embed/`, as in round two.\n',
        'Deliverables: [new records](results/round3/records.jsonl), [merged union](results/round3/union-records.jsonl), [unknown projection](results/round3/UNKNOWN.g6), [summary](results/round3/summary.json), [checker log](results/round3/run/checker.log), [checker report](results/round3/run/out/report.json), [final audit](results/round3/final-audit.json), and [optional-pass decision](results/round3/optional-decision.json).\n',
        '## UNCERTAIN\n',
        '- The optional 990-plus-41 host pass was not exercised because the shared box failed the recorded quiet check. The new converter may close more of those inputs, but no coverage claim is made for them.\n',
        '- This module did not rerun the complete nine-vertex control pipeline. It supplies accepted certificates for all 13 supplied gaps; the supervisor must merge them with the other producers and rerun that control. The module\'s own union still has unknown records.\n',
        '- Numerical host adjacency and approximate real-root selection remain proposal steps. Incorrect proposals can waste time or select a different conjugate, but cannot bypass the exact certificate checks. The most likely future integration defects are unsupported notebook expression forms or a wrong source-coordinate ordering.\n',
        '- H2\'s two translated table rows require the figure to interpret them. The maximum discrepancy from a printed rounded coordinate was about 5.13e-6, so rounded decimals should not be treated as certified intervals. The complex polynomials and all required graph edges were checked exactly.\n',
        '- General PARI OOM recovery was not forced deliberately. The preserved initial probe exercised the timeout under thread-stack pressure. High-degree image fields beyond this sample, and host conversion above the degree cap of 256, remain unmeasured.\n',
        '- H1/H2 use source-specific positive construction constraints, and the G118 method is a library method. These are not the general-search named controls and do not authorize a classification claim.\n']
    report=text.rstrip()+'\n\n'+'\n'.join(body);assert '\u2014' not in report;(HERE/'REPORT.md').write_text(report)
    for name in source_names+['REPORT.md','ROUND3.md']:assert '\u2014' not in (HERE/name).read_text()
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['collect','controls','finish']);a=p.parse_args();globals()[a.command]()
