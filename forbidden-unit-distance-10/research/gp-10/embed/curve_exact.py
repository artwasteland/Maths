"""Rational angle proposals near a traced point, accepted only by exact checks."""
from fractions import Fraction
import math
from pathlib import Path
import time
from msolve_exact import invoke,decode_output,certify
from rigid_system import make_system
from round2 import stored_system,load_system,write_json
from round2_phase import isolated


def pin_candidates(witness):
    theta=witness['angle'];dx=math.cos(theta);dy=math.sin(theta);seen=set();result=[]
    for bound in (16,64,256):
        t=None if abs(1+dx)<1e-12 else Fraction(float(dy/(1+dx))).limit_denominator(bound)
        c,s=(Fraction(-1),Fraction(0)) if t is None else ((1-t*t)/(1+t*t),2*t/(1+t*t))
        if (c,s) in seen:continue
        seen.add((c,s));result.append({'edge':witness['pin_edge'],'cos':str(c),'sin':str(s),'t':None if t is None else str(t),'denominator_bound':bound})
    return result


def solve(code,witness,directory,seconds=120):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);began=time.monotonic();deadline=began+seconds
    meta={'g6':code,'method':'trace_rational_pin_msolve','cap_seconds':seconds,'attempts':[]};cert=None
    proposals=pin_candidates(witness)
    def left():
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('trace_exact:budget_exhausted')
        return remaining
    for i,pin in enumerate(proposals):
        if deadline-time.monotonic()<.05:break
        target=directory/f'attempt-{i:02d}';target.mkdir(exist_ok=True);row={'pin':pin,'frame':witness['frame']};start=time.monotonic()
        try:
            saved=isolated(lambda:stored_system(make_system(code,pins_override=[pin],frame=witness['frame'])),min(3,left()))
            write_json(target/'system.json',saved);system=load_system(target/'system.json')
            available=left();cap=max(.001,(available-min(10.,available/5))/(len(proposals)-i))
            raw,call=invoke(system,target,cap,parse=False);row.update(call)
            if raw is not None:
                def convert():
                    parsed=decode_output(raw,system['variables'],progress=lambda p:write_json(target/'conversion-progress.json',p))
                    return certify(code,system,parsed)
                cert,checked=isolated(convert,min(10,left()));row.update(checked)
                assert not checked.get('triage'), 'trace_pin_must_not_produce_triage'
        except Exception as exc:row['reason']=type(exc).__name__+':'+str(exc)[:400]
        row['wall_seconds']=time.monotonic()-start;write_json(target/'stats.json',row);meta['attempts'].append(row)
        if cert is not None:break
    meta['wall_seconds']=time.monotonic()-began;meta['reason']='exact_embedding' if cert is not None else 'numeric_distinct_but_exact_unresolved'
    if cert is not None:meta['degree']=len(cert['field']['minpoly'])-1
    write_json(directory/'stats.json',meta);return cert,meta
