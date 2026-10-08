"""Paired command-entry, resume and trivial-graph controls."""
from copy import deepcopy
import json
import runpy
import sys
from generic_exact import run
from exact import verify
from msolve_exact import limits,sha
from round2 import HERE,write_json

OUT=HERE/'results/round4/controls/entry'

def main():
    limits();OUT.mkdir(parents=True,exist_ok=True);source=OUT/'input.g6';source.write_text('Bw\n');results=[]
    for script in ('round2.py','round3.py'):
        target=OUT/script[:-3];argv=[str(HERE/script),'input','--input',str(source),'--out',str(target)]
        def invoke(extra=()):
            old=sys.argv[:];sys.argv=argv+list(extra)
            try:runpy.run_path(str(HERE/script),run_name='__main__')
            except SystemExit as exc:assert exc.code==0
            finally:sys.argv=old
        invoke();record=json.loads((target/'records.jsonl').read_text());assert record['verdict']=='embedded';verify('Bw',record['cert'])
        before=(target/'records.jsonl').read_bytes();invoke();assert before==(target/'records.jsonl').read_bytes()
        flag='--msolve-cap' if script=='round2.py' else '--host-cap'
        try:invoke([flag,'21'])
        except ValueError as exc:assert str(exc)=='resume:input_or_config_changed'
        else:raise AssertionError('changed configuration accepted')
        bad=deepcopy(record['cert']);bad['coords'][0][0][0]='7/1'
        try:verify('Bw',bad)
        except ValueError as exc:assert str(exc)=='edge:0,1'
        else:raise AssertionError('coordinate mutation accepted')
        results.append({'entry':script,'positive':'PASS','coordinate_red':'edge:0,1','resume':'identical','config_red':'resume:input_or_config_changed','record_sha256':sha(before)})
    trivial=OUT/'trivial.g6';trivial.write_text('?\n@\nA?\nA_\n')
    run(trivial,OUT/'trivial',methods=('msolve',))
    for line in (OUT/'trivial/records.jsonl').read_text().splitlines():
        record=json.loads(line);assert record['verdict']=='embedded';verify(record['g6'],record['cert'])
        bad=deepcopy(record['cert']);bad['field']['interval'][0]=bad['field']['interval'][1]
        try:verify(record['g6'],bad)
        except ValueError as exc:assert str(exc)=='sign_change'
        else:raise AssertionError('invalid interval accepted')
        results.append({'g6':record['g6'],'positive':'PASS','interval_red':'sign_change'})
    write_json(OUT/'results.json',results);print(json.dumps(results,indent=2))

if __name__=='__main__':main()
