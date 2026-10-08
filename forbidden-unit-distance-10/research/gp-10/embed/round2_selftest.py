#!/usr/bin/env python3
"""Positive and red controls for the round-two producer and msolve grammar."""
from copy import deepcopy
import json
from pathlib import Path
import time
import os
from fractions import Fraction
from round2_phase import isolated
import networkx as nx
from exact import verify, CertificateError
from msolve_exact import limits, invoke, certify, decode_output, parse_literal, Poly, root_count, prepare_binary
from rigid_system import make_system
from round2 import OUT, write_json


def main():
    limits(); started = time.monotonic(); checks = []
    def passed(name, **details): checks.append({'name': name, 'status': 'PASS', **details})
    def rejected(name, action, reason):
        try: action()
        except (ValueError, CertificateError) as exc:
            assert str(exc).startswith(reason), (name, str(exc), reason)
            passed(name, expected_reason=reason, actual_reason=str(exc))
        else: raise AssertionError(name + ': accepted mutation')
    positives = {}
    for name, graph, pins in [
            ('triangle', nx.complete_graph(3), None),
            ('rhombus', nx.cycle_graph(4), [{'edge': [0, 3], 'cos': '3/5', 'sin': '4/5', 't': '1/2'}]),
            ('K4', nx.complete_graph(4), None),
            ('collisions', nx.complete_bipartite_graph(2, 3), None)]:
        if name == 'collisions': graph.add_edge(0, 1)
        code = nx.to_graph6_bytes(graph, header=False).decode().strip()
        system = make_system(code, pins)
        directory = OUT / 'controls' / name
        parsed, call = invoke(system, directory)
        assert parsed is not None, call
        cert, meta = certify(code, system, parsed)
        write_json(directory / 'result.json', {'g6': code, 'call': call, 'result': meta, 'certificate': cert})
        if name in ('triangle', 'rhombus'):
            assert cert is not None and not meta['triage']
            positives[name] = (code, cert, system, parsed)
            passed(name + '_known_positive', eliminant_degree=parsed['degree'], certificate_degree=len(cert['field']['minpoly'])-1)
        else:
            assert cert is None and meta['triage']
            passed(name + '_no_embedding_triage', solver_status=meta['solver_status'])
            pinned = deepcopy(system); pinned['k'] = 1; pinned['pins'] = [{'test': 'not_a_refutation'}]
            assert not certify(code, pinned, parsed)[1]['triage']
            passed(name + '_pins_forbid_triage')
    code, cert, system, parsed = positives['triangle']
    bad = deepcopy(cert); bad['coords'][1][0][0] = '2/1'
    rejected('one_coordinate_red', lambda: verify(code, bad), 'edge:0,1')
    bad = deepcopy(cert); bad['field']['interval'][0] = bad['field']['interval'][1]
    rejected('one_interval_endpoint_red', lambda: verify(code, bad), 'sign_change')
    bad_parse = dict(parsed); bad_parse['boxes'] = bad_parse['boxes'][:-1]
    rejected('missing_root_box_red', lambda: certify(code, system, bad_parse), 'parametrization:root_count')
    bad_parse = dict(parsed); bad_parse['numerators'] = list(parsed['numerators'])
    numerator, divisor = bad_parse['numerators'][0]
    bad_parse['numerators'][0] = (numerator + parsed['den'] * divisor, divisor)
    rejected('one_parametrized_coordinate_red', lambda: certify(code, system, bad_parse), 'parametrization:equation:')
    raw = (OUT / 'controls/triangle/output.ms').read_text()
    bad_raw = raw.replace("'x2'", "'not_x2'", 1)
    rejected('one_variable_name_red', lambda: decode_output(bad_raw, system['variables']), 'parse:variable_order_or_separator')
    rejected('truncated_output_red', lambda: decode_output(raw.rstrip()[:-1], system['variables']), 'parse:missing_terminator')
    rejected('false_basis_one_red', lambda: decode_output('[1]:', system['variables']), 'parse:unrecognized_status')
    bad_system = deepcopy(system); bad_system['text'] = bad_system['text'].replace('x2^2', '(x2)^2', 1)
    rejected('parenthesized_input_red', lambda: invoke(bad_system, OUT / 'controls/parentheses'), 'input:expansion_or_size')
    code, cert, system, parsed = positives['rhombus']
    bad = deepcopy(cert); bad['coords'][2] = deepcopy(bad['coords'][0])
    rejected('coincident_points_with_edges_exact_red', lambda: verify(code, bad), 'distinctness:0,2:zero')
    assert parsed['parameter_order'] != system['variables']
    passed('reordered_variables_use_reordered_root_boxes')
    # Same graph and input, msolve may add a generic separator. Hashes must repeat.
    parsed2, call2 = invoke(system, OUT / 'controls/rhombus-repeat')
    assert (OUT / 'controls/rhombus/output.ms').read_bytes() == (OUT / 'controls/rhombus-repeat/output.ms').read_bytes()
    assert certify(code, system, parsed2)[0] == cert
    passed('deterministic_parametrization', output_sha256=call2['output_sha256'])
    collision_raw = (OUT / 'controls/collisions/output.ms').read_text()
    collision_graph = nx.complete_bipartite_graph(2, 3); collision_graph.add_edge(0, 1)
    collision_code = nx.to_graph6_bytes(collision_graph, header=False).decode().strip()
    collision_system = make_system(collision_code)
    repeated, repeated_call = invoke(collision_system, OUT / 'controls/collisions-repeat')
    assert repeated['added_separator']
    assert collision_raw == (OUT / 'controls/collisions-repeat/output.ms').read_text()
    passed('deterministic_added_separator', output_sha256=repeated_call['output_sha256'])
    assert root_count(Poly([1, 0, 1])) == 0 and root_count(Poly([-1, 0, 1])) == 2
    passed('sturm_real_versus_nonreal')
    parsed3, call3 = invoke(system, OUT / 'controls/timeout', seconds=0.000001)
    assert parsed3 is None and call3['timeout'] and call3['reason'] == 'msolve_timeout'
    passed('child_timeout_is_unknown', returncode=call3['returncode'])
    path_code = nx.to_graph6_bytes(nx.path_graph(3), header=False).decode().strip()
    nonradical = {'g6': path_code, 'variables': ['x2', 'y2'], 'frame': [0, 1], 'k': 1,
        'pins': [{'test': 'squared_y_pin'}],
        'text': 'x2,y2\n0\nx2^2-2*x2+y2^2,\ny2^2\n',
        'polynomials': [{(2, 0): Fraction(1), (1, 0): Fraction(-2), (0, 2): Fraction(1)},
                        {(0, 2): Fraction(1)}]}
    reduced, _ = invoke(nonradical, OUT / 'controls/nonradical')
    assert reduced['ideal_degree'] > reduced['degree']
    nonradical_cert, nonradical_meta = certify(path_code, nonradical, reduced)
    assert nonradical_cert is not None and not nonradical_meta['triage']
    passed('multiplicity_degree_exceeds_eliminant_positive', ideal_degree=reduced['ideal_degree'], degree=reduced['degree'])
    bad = deepcopy(nonradical_cert); bad['coords'][2][0][0] = '3/1'
    rejected('nonradical_coordinate_red', lambda: verify(path_code, bad), 'edge:1,2')
    assert isolated(lambda: {'value': 7}, 1) == {'value': 7}
    passed('isolated_phase_positive')
    rejected('isolated_phase_native_exit_red', lambda: isolated(lambda: os._exit(23), 1), 'phase:child_exit:23')
    rejected('isolated_phase_timeout_red', lambda: isolated(lambda: time.sleep(10), .02), 'phase:hard_timeout')
    # Save one canonical positive for the independent checker controls.
    code, cert, _, _ = positives['triangle']
    write_json(OUT / 'controls/official-positive-record.json', {'g6': code, 'verdict': 'embedded', 'cert': cert})
    result = {'checks': checks, 'passed': len(checks), 'wall_seconds': time.monotonic()-started,
              'binary': prepare_binary()[1]}
    write_json(OUT / 'selftest-results.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
