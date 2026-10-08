"""Bounded numerical angle continuation, with explicit non-proof diagnostics."""
import os
os.environ['SYMPY_GROUND_TYPES']='python'
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
from collections import Counter
import json
import math
from pathlib import Path
import time
import numpy as np
from scipy.optimize import least_squares
from exact import graph6
from rigid_system import seed_for,rigidity
from generic_exact import frame_variants
from numeric import fit
from round2 import write_json

CONFIG={'frames':3,'pins_per_frame':2,'starting_points':3,'grid':144,'max_nfev':60,
        'edge_tolerance':1e-9,'distinct_margin':1e-3,'seconds':120.0,
        'method':'analytic-Jacobian angle continuation, both sweep directions across starts'}


def assess(code,points,edge_tolerance=1e-9,distinct_margin=1e-3):
    n,edges=graph6(code);p=np.asarray(points,dtype=float)
    if p.shape!=(n,2) or not np.isfinite(p).all():return {'reason':'nonfinite_or_shape','real_sample':False,'distinct_sample':False}
    error=max((abs(float(np.dot(p[u]-p[v],p[u]-p[v]))-1) for u,v in edges),default=0.)
    sep,u,v=min((float(np.linalg.norm(p[u]-p[v])),u,v) for v in range(n) for u in range(v))
    real=error<=edge_tolerance;distinct=real and sep>=distinct_margin
    return {'edge_error':error,'minimum_pair_distance':sep,'closest_pair':[u,v],
        'real_sample':real,'distinct_sample':distinct,'reason':'distinct_sample' if distinct else ('collision_margin' if real else 'edge_residual')}


class Problem:
    def __init__(self,code,frame,pin):
        self.n,edges=graph6(code);self.frame=list(frame);self.pin=list(pin)
        self.free=[v for v in range(self.n) if v not in frame];self.columns={v:i for i,v in enumerate(self.free)}
        self.edges=[e for e in edges if list(e) not in (list(frame),list(pin))]
        self.fixed=np.zeros((self.n,2));self.fixed[frame[1],0]=1
        self.B=np.zeros((len(self.edges),len(self.free)))
        for i,(u,v) in enumerate(self.edges):
            for w,sign in ((u,1),(v,-1)):
                if w in self.columns:self.B[i,self.columns[w]]=sign
        self.e=np.asarray(self.edges,dtype=int)
        self.P=np.zeros((2,2*len(self.free)))
        for w,sign in ((pin[1],1),(pin[0],-1)):
            if w in self.columns:
                self.P[0,2*self.columns[w]]=sign;self.P[1,2*self.columns[w]+1]=sign
    def unpack(self,z):
        p=self.fixed.copy();p[self.free]=np.asarray(z).reshape(-1,2);return p
    def values(self,z,direction):
        p=self.unpack(z);delta=p[self.e[:,0]]-p[self.e[:,1]]
        return np.concatenate((np.einsum('ij,ij->i',delta,delta)-1,p[self.pin[1]]-p[self.pin[0]]-direction))
    def jacobian(self,z):
        p=self.unpack(z);delta=p[self.e[:,0]]-p[self.e[:,1]]
        j=np.empty((len(self.edges),2*len(self.free)))
        j[:,0::2]=2*delta[:,0,None]*self.B;j[:,1::2]=2*delta[:,1,None]*self.B
        return np.vstack((j,self.P))


def select_pins(code,frame,count):
    n,edges=graph6(code);free=[v for v in range(n) if v not in frame]
    rng=np.random.default_rng((seed_for(code)+1009*frame[0]+1013*frame[1])%(2**64))
    points=rng.normal(size=(n,2));points[frame[0]]=[0,0];points[frame[1]]=[1,0]
    matrix=np.asarray(rigidity(n,edges,points,free));u,s,vh=np.linalg.svd(matrix,full_matrices=True)
    null=vh[int(np.sum(s>1e-9)):];cols={v:i for i,v in enumerate(free)};scores=[]
    for a,b in edges:
        if [a,b]==list(frame):continue
        dx,dy=points[b]-points[a];row=np.zeros(2*len(free))
        for w,sign in ((b,1),(a,-1)):
            if w in cols:row[2*cols[w]:2*cols[w]+2]=sign*np.array([-dy,dx])
        score=float(np.linalg.norm(null@row)/max(np.linalg.norm(row),1e-20));scores.append((score,[a,b]))
    scores.sort(key=lambda x:(-x[0],x[1]));return [{'edge':edge,'generic_nullspace_coupling':score} for score,edge in scores[:count]]


def trace(code,directory,config=None):
    cfg=dict(CONFIG if config is None else config);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    began=time.monotonic();deadline=began+cfg['seconds'];n,edges=graph6(code)
    frames=[r['frame'] for r in frame_variants(code,0,frames=cfg['frames'],pins=1)]
    stats={'g6':code,'config':cfg,'frames':[],'samples':0,'real_samples':0,'completed_series':0,
        'planned_series':len(frames)*cfg['pins_per_frame']*cfg['starting_points'],'sampled_distinct':False,
        'completed_grid':False,'best_minimum_pair_distance':None,'minimum_pair_distance_seen':None,
        'least_edge_residual':None,'collision_pairs':{},'witness':None}
    pairs=Counter();best=None;budget_hit=False
    with (directory/'samples.jsonl').open('w') as stream:
        try:
            for fi,frame in enumerate(frames):
                pins=select_pins(code,frame,cfg['pins_per_frame']);stats['frames'].append({'frame':frame,'pins':pins})
                ordered=[tuple(frame)]+[e for e in edges if list(e)!=frame]
                seeds=[]
                for si in range(cfg['starting_points']):
                    if time.monotonic()>deadline:raise TimeoutError('trace:soft_budget')
                    p,meta=fit(n,ordered,seed_for(code)+fi*15485863+si*32452843,restarts=1)
                    seeds.append(p)
                for pi,pinrow in enumerate(pins):
                    pin=pinrow['edge'];problem=Problem(code,frame,pin)
                    for si,initial in enumerate(seeds):
                        delta=initial[pin[1]]-initial[pin[0]];offset=math.atan2(float(delta[1]),float(delta[0]))
                        previous=initial[problem.free].ravel();previous2=None;direction_sign=-1 if si%2 else 1
                        for gi in range(cfg['grid']):
                            if time.monotonic()>deadline:raise TimeoutError('trace:soft_budget')
                            angle=offset+direction_sign*2*math.pi*gi/cfg['grid'];direction=np.array([math.cos(angle),math.sin(angle)])
                            predictor=previous if previous2 is None else 2*previous-previous2
                            result=least_squares(lambda z:problem.values(z,direction),predictor,jac=lambda z:problem.jacobian(z),method='lm',max_nfev=cfg['max_nfev'],ftol=1e-11,xtol=1e-11,gtol=1e-11)
                            p=problem.unpack(result.x);diag=assess(code,p,cfg['edge_tolerance'],cfg['distinct_margin'])
                            pin_error=float(np.max(np.abs(p[pin[1]]-p[pin[0]]-direction)))
                            real=diag['real_sample'] and pin_error<=cfg['edge_tolerance']
                            distinct=real and diag['distinct_sample']
                            row={'frame_index':fi,'pin_index':pi,'start':si,'grid_index':gi,'angle':angle,'pin_error':pin_error,
                                'nfev':int(result.nfev),'real_sample':real,'distinct_sample':distinct,
                                **{key:diag[key] for key in ('edge_error','minimum_pair_distance','closest_pair')}}
                            stream.write(json.dumps(row)+'\n');stats['samples']+=1
                            err=diag['edge_error'];stats['least_edge_residual']=err if stats['least_edge_residual'] is None else min(err,stats['least_edge_residual'])
                            if real:
                                stats['real_samples']+=1;sep=diag['minimum_pair_distance']
                                stats['minimum_pair_distance_seen']=sep if stats['minimum_pair_distance_seen'] is None else min(sep,stats['minimum_pair_distance_seen'])
                                if stats['best_minimum_pair_distance'] is None or sep>stats['best_minimum_pair_distance']:
                                    stats['best_minimum_pair_distance']=sep;best={'points':p.tolist(),'frame':frame,'pin_edge':pin,'angle':angle,'diagnostics':row}
                                if not distinct:pairs[str(diag['closest_pair'])]+=1
                                previous2,previous=previous,result.x
                            else:previous=result.x;previous2=None
                            if distinct:
                                stats['sampled_distinct']=True;stats['witness']=best
                                raise StopIteration
                        stats['completed_series']+=1;stream.flush()
                        write_json(directory/'progress.json',stats)
            stats['completed_grid']=True
        except StopIteration:pass
        except TimeoutError:budget_hit=True
    stats['collision_pairs']=dict(pairs);stats['best_sample']=best;stats['budget_exhausted']=budget_hit
    stats['reason']='distinct_numeric_sample' if stats['sampled_distinct'] else ('incomplete_grid_budget' if budget_hit else ('all_sampled_real_configurations_collide_within_margin' if stats['real_samples'] else 'no_converged_real_sample_on_angle_sections'))
    stats['wall_seconds']=time.monotonic()-began;write_json(directory/'trace.json',stats);return stats
