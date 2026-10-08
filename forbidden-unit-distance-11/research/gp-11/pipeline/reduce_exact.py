"""Re-express a positive coordinate proposal with GP10's existing field code."""
from common import *
import hashlib, subprocess, json
from gp_field import PRELUDE
from extension import gp_poly, gp_output

def reduce_candidate(code, cert, directory, seconds):
    directory.mkdir(parents=True, exist_ok=True)
    p = gp_poly(cert['field']['minpoly'])
    lo, hi = cert['field']['interval']
    init = 'P=' + p + ';rr=polrootsreal(P);idx=0;for(j=1,#rr,if(rr[j]>' + lo + ' && rr[j]<' + hi + ',idx=j;break));if(idx==0,error("base:root"));TH=rr[idx];R=List();'
    ops = ['push(' + gp_poly(axis) + ');' for point in cert['coords'] for axis in point]
    # Try an existing coordinate as primitive element before a large linear
    # combination. All resulting algebraic coordinates are independently
    # checked; this changes only the producer's representation search.
    old = 'for(trial=1,8,T=sum(j=1,d,(j+trial-1)^trial*R[ids[j]]);'
    new = 'for(trial=1,d+8,T=if(trial<=d,R[ids[trial]],sum(j=1,d,(j+trial-d-1)^(trial-d)*R[ids[j]]));'
    assert old in PRELUDE
    prelude = PRELUDE.replace(old, new)
    source = 'setrand(' + str(int(hashlib.sha256(code.encode()).hexdigest()[:16], 16)) + ');\n' + prelude + '\nmain()={\n' + init + '\n' + '\n'.join(ops) + '\nfinish(' + str(list(range(1, 2 * len(cert['coords']) + 1))) + ');\n};\nmain();\nquit;\n'
    path = directory / 'reduce.gp'
    path.write_text(source)
    start = time.monotonic()
    child = subprocess.Popen(['gp', '-fq', '-s', '128000000', str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = child.communicate(timeout=seconds)
    except BaseException:
        child.kill()
        child.communicate()
        raise
    (directory / 'reduce.stdout').write_text(stdout)
    (directory / 'reduce.stderr').write_text(stderr)
    reduced = gp_output(code, stdout, len(cert['coords']))
    meta = {'seconds': time.monotonic() - start, 'input_certificate_bytes': len(json.dumps(cert)), 'output_certificate_bytes': len(json.dumps(reduced)), 'input_degree': len(cert['field']['minpoly']) - 1, 'output_degree': len(reduced['field']['minpoly']) - 1, 'primitive_element_order': 'Existing coordinate first, then GP10 weighted coordinate combinations'}
    return (reduced, meta)
