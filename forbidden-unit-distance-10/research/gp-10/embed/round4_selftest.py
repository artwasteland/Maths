"""Paired controls for generic frame, pin, host and resume modes."""
from copy import deepcopy
from pathlib import Path
from fractions import Fraction
import json
import time
import networkx as nx
from generic_exact import *
from exact import CertificateError
import round2_selftest

OUT=HERE/'results/round4/controls'

def main():
    limits();OUT.mkdir(parents=True,exist_ok=True);began=time.monotonic();checks=[]
    round2_selftest.OUT=OUT/'legacy'
    round2_selftest.main()
    def good(name,**detail):checks.append(dict(name=name,status='PASS',**detail))
    def red(name,fn,reason):
        try:fn()
        except Exception as exc:
            assert str(exc).startswith(reason),(name,str(exc),reason)
            good(name,reason=str(exc))
        else:raise AssertionError(name+':accepted')
    def pair(name,code,cert):
        verify(code,cert);good(name,degree=len(cert['field']['minpoly'])-1)
        u,v=graph6(code)[1][0];bad=deepcopy(cert)
        bad['coords'][u][0][0]=textq(str(Fraction(bad['coords'][u][0][0])+7))
        red(name+'_coordinate_red',lambda:verify(code,bad),'edge:'+str(u)+','+str(v))
    for name,graph in [('triangle',nx.complete_graph(3)),('cycle4',nx.cycle_graph(4))]:
        code=nx.to_graph6_bytes(graph,header=False).decode().strip();k=0 if name=='triangle' else 1
        systems=[]
        for i,variant in enumerate(frame_variants(code,k)):
            system=make_system(code,**variant);systems.append(system)
            assert system['frame']==variant['frame'] and system['k']==k
            parsed,meta=invoke(system,OUT/name/str(i),seconds=5)
            assert parsed is not None,meta
            cert,meta=certify(code,system,parsed);assert cert is not None,meta
            pair(name+'_variant_'+str(i),code,cert)
        assert len({tuple(s['frame']) for s in systems})==3
        if k:
            assert len({json.dumps(s['pins'],sort_keys=True) for s in systems})>1
            bad=deepcopy(systems[0]['pins']);bad[0]['cos']='2'
            red('pin_unit_direction_red',lambda:make_system(code,pins_override=bad),'pinning:not_a_rational_unit_direction')
            red('nonedge_frame_red',lambda:make_system(code,frame=[0,2]),'system:frame_not_edge')
    host=database()['G118'];code='H?DTJQx'
    cert,meta=host_stage(code,OUT/'g118',host,10);assert cert is not None,meta
    pair('g118_degree16',code,cert)
    raw=(OUT/'g118/field.log').read_text();assert gp_output(code,raw,9)==cert
    red('pari_success_marker_red',lambda:gp_output(code,raw.replace('GP_FIELD_OK','GP_FIELD_NO'),9),'pari:missing_exact_success')
    cert,meta=host_stage(code,OUT/'g118-timeout',host,.000001)
    assert cert is None and 'budget_exhausted' in meta['reason'];good('g118_budget_exhausted_unknown',reason=meta['reason'])
    code=nx.to_graph6_bytes(nx.complete_graph(3),header=False).decode().strip()
    source=OUT/'resume-input.g6';source.write_text(code+'\n')
    run(source,OUT/'resume',methods=('msolve',))
    before=(OUT/'resume/records.jsonl').read_bytes()
    run(source,OUT/'resume',methods=('msolve',))
    assert (OUT/'resume/records.jsonl').read_bytes()==before;good('resume_identical_records')
    red('resume_config_red',lambda:run(source,OUT/'resume',methods=('msolve',),msolve_cap=21),'resume:input_or_config_changed')
    source.write_text(code+'\n'+code+'\n')
    red('resume_input_red',lambda:run(source,OUT/'resume',methods=('msolve',)),'resume:input_or_config_changed')
    source.write_text(code+'\n')
    result={'checks':checks,'passed':len(checks),'legacy_passed':json.loads((OUT/'legacy/selftest-results.json').read_text())['passed'],'wall_seconds':time.monotonic()-began}
    write_json(OUT/'results.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
