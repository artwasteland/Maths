"""Paired numerical, continuation and exact-conversion controls for Round 5."""
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
import networkx as nx
from curve_trace import CONFIG,trace,assess,Problem
from curve_exact import solve
from msolve_exact import limits
from round2_phase import isolated
from round2 import HERE,write_json
from exact import verify,rational,textq

OUT=HERE/'results/round5/controls'

def main():
    limits();OUT.mkdir(parents=True,exist_ok=True);start=time.monotonic();checks=[]
    code=nx.to_graph6_bytes(nx.cycle_graph(4),header=False).decode().strip()
    square=[[0,0],[1,0],[1,1],[0,1]]
    assert assess(code,square)['distinct_sample'];bad=deepcopy(square);bad[0][0]=7
    assert assess(code,bad)['reason']=='edge_residual'
    checks.append({'positive':'square_numerical','red':'one_coordinate','reason':'edge_residual'})
    bad=deepcopy(square);bad[2]=bad[0][:];r=assess(code,bad)
    assert r['reason']=='collision_margin' and r['edge_error']==0 and r['minimum_pair_distance']==0
    checks.append({'positive':'square_numerical','red':'one_vertex_position','reason':'collision_margin_with_edges_exact'})
    problem=Problem(code,[0,1],[0,3]);z=np.array([.7,.9,-.2,1.1]);direction=np.array([0.,1.]);h=1e-6
    numeric=np.column_stack([(problem.values(z+np.eye(len(z))[i]*h,direction)-problem.values(z-np.eye(len(z))[i]*h,direction))/(2*h) for i in range(len(z))])
    exact=problem.jacobian(z);assert np.max(np.abs(exact-numeric))<1e-8
    bad=exact.copy();bad[0,0]+=1;assert np.max(np.abs(bad-numeric))>.9
    checks.append({'positive':'analytic_Jacobian_matches_difference','red':'one_Jacobian_entry','reason':'derivative_mismatch'})
    positive=isolated(lambda:trace(code,OUT/'cycle4'),125)
    assert positive['sampled_distinct'] and positive['witness']['diagnostics']['minimum_pair_distance']>=CONFIG['distinct_margin']
    forbidden=nx.to_graph6_bytes(nx.complete_bipartite_graph(2,3),header=False).decode().strip()
    negative=isolated(lambda:trace(forbidden,OUT/'K23'),125)
    assert not negative['sampled_distinct'] and negative['completed_grid'] and negative['samples']==2592
    assert negative['real_samples']>0 and negative['reason']=='all_sampled_real_configurations_collide_within_margin'
    checks.append({'positive':'cycle4_continuation','red':'g6_field_changed_to_K23','reason':negative['reason'],'red_samples':negative['samples']})
    cert,meta=solve(code,positive['witness'],OUT/'exact',120);assert cert is not None,meta
    verify(code,cert);bad=deepcopy(cert);bad['coords'][0][0][0]=textq(rational(bad['coords'][0][0][0])+7)
    try:verify(code,bad)
    except ValueError as exc:assert str(exc)=='edge:0,1'
    else:raise AssertionError('exact_coordinate_mutation_accepted')
    checks.append({'positive':'trace_to_rational_pin_exact','red':'one_exact_coordinate','reason':'edge:0,1'})
    # A changed numeric configuration is never allowed to bypass exact conversion.
    bad=deepcopy(cert);bad['field']['interval'][0]=bad['field']['interval'][1]
    try:verify(code,bad)
    except ValueError as exc:assert str(exc)=='sign_change'
    else:raise AssertionError('interval_mutation_accepted')
    checks.append({'positive':'trace_to_rational_pin_exact','red':'one_interval_endpoint','reason':'sign_change'})
    write_json(OUT/'positive-record.json',{'g6':code,'verdict':'embedded','cert':cert})
    result={'status':'PASS','paired_checks':checks,'count':len(checks),'wall_seconds':time.monotonic()-start,'trace_config':CONFIG}
    write_json(OUT/'results.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
