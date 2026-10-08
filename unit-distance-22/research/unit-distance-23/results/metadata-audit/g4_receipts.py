from pathlib import Path
from collections import Counter, defaultdict
import sys,json
sys.dont_write_bytecode=True
R=Path('<repo>');S=Path('<scratch>/scratchpad');O=Path('/tmp/metadata-audit')
sys.path.insert(0,str(R/'research/unit-distance-23/tools'))
import target_check as tc
vc=tc.vc();out=[]
for name,root,sub,target in [('fleet',S/'fleet/results','u23','23-65'),('control22',S/'control22','u23','22-61'),('calibration',S/'calib-snap','calib-21-57','21-57')]:
    ds=sorted(root.glob(f'*/research/unit-distance-23/results/{sub}/{target}-L12-tri-pf74/s*of1920'))
    modes=Counter();verdicts=Counter();bad=[];stage_files=0;red=0
    for d in ds:
        fp=json.loads((d/'replay/fingerprint.json').read_text());sm=json.loads((d/'replay/summary.json').read_text());i=int(d.name[1:].split('of')[0])
        verdict,why=vc.g4_verdict(fp,sm,[12,i,1920],{}, {}, {})
        if why or verdict!=fp['result']:bad.append((str(d),verdict,why))
        modes[fp['mode']]+=1;verdicts[verdict]+=1
        stages={tuple(s['level']) for s in sm['stages'] if s.get('kind')=='keep+slice'}
        if stages!={(12,m) for m in range(20 if target!='21-57' else 21,28)}:bad.append((str(d),'slice stage coverage',sorted(stages)))
        stage_files+=len(stages)
        if fp['mode']=='full':
            if all(tc.red_ok(r) for r in sm['red_controls']):red+=1
            else:bad.append((str(d),'red details'))
    line=f'{name}: copies {len(ds)}, derived verdicts {dict(verdicts)}, modes {dict(modes)}, full copies with red outcomes {red}, slice-stage records {stage_files}, verdict or slice-stage errors {len(bad)}'
    print(line,flush=True);out.append(line)
    if bad:print(bad[:4],flush=True)
    assert not bad
(O/'g4-receipts.txt').write_text('\n'.join(out)+'\n')
