"""Reconstruct GP's two exceptional hosts and check their printed polynomials."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import time
from msolve_exact import limits,invoke,decode_output,Poly,Q,integer_coefficients,substitute
from exact import graph6,adjacency,verify,CertificateError,textq
from hosts import monomorphism,check_mapping
from round2 import write_json
from round2_phase import isolated
from round3 import OUT,HERE

SOURCE=HERE.parent.parent/'unit-distance-22/sources/gp/smallUD.tex'


def polynomial(text):
    s=re.sub(r'\s+','',text.replace(r'\;','').replace('{','').replace('}',''))
    terms=re.findall(r'[+-]?[^+-]+',s);coeff={}
    for term in terms:
        m=re.fullmatch(r'([+-]?)(\d*)(?:z(?:\^(\d+))?)?',term)
        if not m:raise ValueError('table:polynomial:'+term)
        sign=-1 if m[1]=='-' else 1
        degree=int(m[3] or 1) if 'z' in term else 0
        value=sign*int(m[2] or 1);coeff[degree]=coeff.get(degree,0)+value
    return [coeff.get(i,0) for i in range(max(coeff)+1)]


def tables():
    source=SOURCE.read_text();out={}
    for name in ('H1','H2'):
        part=source.split(r'\label{'+name.lower()+'table}',1)[1].split(r'\end{tabular}',1)[0]
        rows=[]
        for line in part.splitlines():
            if line.lstrip().startswith('%'):continue
            cells=re.findall(r'\$([^$]*)\$',line)
            if len(cells)==3 and re.fullmatch(r'[+-]?\d+\.\d+',cells[0]):
                rows.append({'rounded':[cells[0],cells[1]],'polynomial_text':cells[2]})
            elif len(cells)==1 and line.lstrip().startswith('&'):
                rows[-1]['polynomial_text']+=cells[0]
        assert len(rows)==9,(name,len(rows))
        for row in rows:row['minpoly']=polynomial(row['polynomial_text'])
        out[name]=rows
    return out


def build(name):
    import sympy as sp
    import networkx as nx
    a,b,c,d,s=sp.symbols('a b c d s');variables=[a,b,c,d,s];half=sp.Rational(1,2)
    if name=='H1':
        points=[(0,0),(1,0),(2,0),(half,s/2),(3*half,s/2),
                (a+c,b+d),(a+(-c+s*d)/2,b+(-s*c-d)/2),(a,b),(a+(c+s*d)/2,b+(-s*c+d)/2)]
        edges=[(0,1),(1,2),(2,4),(4,3),(3,0),(3,1),(1,4),(4,5),(5,7),(7,6),(6,8),(8,5),(7,8),(0,7),(2,6)]
    else:
        points=[(0,0),(s,0),(s/2,half),(s/2,-half),(s+c,d),(a,b),((a-s*b)/2,(s*a+b)/2),
                (s+(c-s*d)/2,(s*c+d)/2),(s+(c+s*d)/2,(-s*c+d)/2)]
        edges=[(0,2),(2,1),(1,3),(3,0),(2,3),(1,8),(8,4),(4,7),(7,1),(0,5),(5,6),(6,0),(5,7),(6,8),(1,4)]
    equations=[s*s-3]
    for u,v in edges:
        expr=sp.expand((points[u][0]-points[v][0])**2+(points[u][1]-points[v][1])**2-1)
        expr=sp.rem(expr,s*s-3,s)
        if expr:equations.append(expr)
    equations=list(dict.fromkeys(equations))
    def terms(expr):
        return {tuple(p):Fraction(int(q.p),int(q.q)) for p,q in sp.Poly(expr,*variables).terms()}
    text_eq=[str(sp.Poly(eq,*variables).clear_denoms()[1].primitive()[1].as_expr()).replace('**','^').replace(' ','') for eq in equations]
    graph=nx.Graph();graph.add_nodes_from(range(9));graph.add_edges_from(edges)
    code=nx.to_graph6_bytes(graph,header=False).decode().strip()
    return {'g6':code,'variables':list(map(str,variables)),'text':','.join(map(str,variables))+'\n0\n'+',\n'.join(text_eq)+'\n',
            'polynomials':[terms(e) for e in equations],'points':[[terms(x),terms(y)] for x,y in points],
            's':terms(s),'edges':sorted(tuple(sorted(e)) for e in edges),'source_formulas':[[str(x),str(y)] for x,y in points]}


def complex_poly(coeff,x,y,f):
    re_part=im_part=Poly([])
    for c in reversed(coeff):
        re_part,im_part=(re_part*x-im_part*y+c)%f,(re_part*y+im_part*x)%f
    return re_part,im_part


def check_table(name,points,s,f,rows):
    for i,(x,y) in enumerate(points):
        if name=='H2' and i in (7,8):x=(x-s)%f
        a,b=complex_poly(rows[i]['minpoly'],x,y,f)
        if a or b:raise ValueError(f'table:minpoly:{i}')


def solution(name,system,raw,rows):
    parsed=decode_output(raw,system['variables'])
    if parsed['status']!='finite':raise ValueError('special:not_finite:'+parsed['status'])
    target=[[float(v) for v in r['rounded']] for r in rows]
    if name=='H2':
        for i in (7,8):target[i][0]+=3**.5
    rejected=[]
    for f,e in sorted(parsed['p'].factor()[1],key=lambda fe:fe[0].degree()):
        if e!=1 or f.degree()>256:continue
        gcd,inverse,_=(parsed['den']%f).xgcd(f)
        if gcd!=Poly([1]):continue
        values=[(-((num%f)*inverse)/divisor)%f for num,divisor in parsed['numerators']]+[Poly([0,1])%f]
        functions=dict(zip(parsed['parameter_order'],values));ordered=[functions[v] for v in system['variables']]
        if any(substitute(eq,ordered,f) for eq in system['polynomials']):continue
        points=[[substitute(c,ordered,f) for c in pt] for pt in system['points']];s=substitute(system['s'],ordered,f)
        try:check_table(name,points,s,f,rows)
        except ValueError as exc:rejected.append(str(exc));continue
        for lo,hi in parsed['root_intervals']:
            lo=Q(str(lo));hi=Q(str(hi))
            if lo==hi:
                if f(lo)!=0:continue
                lo-=Q(1,2**120);hi+=Q(1,2**120)
            if f(lo)*f(hi)>=0:continue
            middle=(lo+hi)/2
            error=max(abs(float(c(middle))-target[i][j]) for i,pt in enumerate(points) for j,c in enumerate(pt))
            if error>0.00003:continue
            degree=f.degree();cert={'type':'exact','field':{'minpoly':integer_coefficients(f),'interval':[textq(lo),textq(hi)]},
                'coords':[[[textq(c[i]) for i in range(degree)] for c in point] for point in points]}
            cert=verify(system['g6'],cert,max_refinements=256)
            return cert,{'degree':degree,'eliminant_degree':parsed['degree'],'table_polynomials_verified':9,
                         'rounded_coordinate_max_error':error,'rejected_other_factors':rejected}
    raise ValueError('special:no_table_matching_exact_embedding:'+str(rejected))


def run(name,rows):
    limits();start=time.monotonic();directory=OUT/name;directory.mkdir(exist_ok=True)
    system=build(name)
    write_json(directory/'source.json',{'table':rows,'source_formulas':system['source_formulas'],'source_g6':system['g6'],'edges':system['edges'],
        'H2_translation':('Add sqrt(3) to table x coordinates 7 and 8, as in uglyFigure.' if name=='H2' else None)})
    raw,call=invoke(system,directory,seconds=180,parse=False);write_json(directory/'solver-call.json',call)
    if raw is None:raise ValueError('special:solver:'+str(call))
    cert,meta=isolated(lambda:solution(name,system,raw,rows),120)
    write_json(directory/'source-certificate.json',cert)
    canonical=subprocess.run(['nauty-labelg','-q'],input=system['g6']+'\n',text=True,capture_output=True,timeout=10,check=True).stdout.strip()
    n,edges=graph6(canonical);mapping,nodes=monomorphism(adjacency(n,edges),adjacency(9,system['edges']),100000)
    check_mapping(adjacency(n,edges),adjacency(9,system['edges']),mapping)
    canon_cert=verify(canonical,dict(cert,coords=[cert['coords'][i] for i in mapping]),max_refinements=256)
    write_json(directory/'record.json',{'g6':canonical,'verdict':'embedded','cert':canon_cert})
    bad=deepcopy(cert);bad['coords'][0][0][0]=textq(Q(bad['coords'][0][0][0])+1)
    try:verify(system['g6'],bad)
    except CertificateError as exc:reason=str(exc);assert reason.startswith('edge:')
    else:raise AssertionError('special:coordinate_mutation_accepted')
    f=Poly(cert['field']['minpoly']);points=[[Poly([Q(v) for v in c]) for c in p] for p in cert['coords']]
    spoint=points[1][0] if name=='H2' else 2*points[3][1]
    mutated=deepcopy(rows);mutated[0]['minpoly'][0]+=1
    try:check_table(name,points,spoint,f,mutated)
    except ValueError as exc:table_reason=str(exc);assert table_reason=='table:minpoly:0'
    else:raise AssertionError('special:table_mutation_accepted')
    meta.update(name=name,g6=canonical,map_to_source=mapping,seconds=time.monotonic()-start,
                control_positive='PASS',coordinate_red=reason,table_red=table_reason)
    write_json(directory/'result.json',meta);print(json.dumps(meta),flush=True)


if __name__=='__main__':
    limits();all_tables=tables();write_json(OUT/'printed-tables.json',all_tables)
    for name in ('H1','H2'):run(name,all_tables[name])
