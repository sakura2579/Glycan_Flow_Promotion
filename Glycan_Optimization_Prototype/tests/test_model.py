"""Scientific regression and UI-input safety checks for the toy demonstrator."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import networkx as nx
import pytest
from model import (
    BASE_EDGES, METHODS, OBSERVED_PROFILE, SUPPLY, TERMINALS,
    build_model, closest_baseline, maximum_flow, objective_weights,
    solve_inverse, solve_stage2,
)


@pytest.mark.parametrize('method', METHODS)
def test_forward_flow_constraints_and_maximum(method):
    m=build_model()
    solution=solve_stage2(m,method)
    assert solution['max_flow']==pytest.approx(120,abs=1e-8)
    assert max(solution['errors'].values()) < 3e-5
    assert sum(solution['profile'].values()) == pytest.approx(1,abs=1e-8)
    assert all(0<=p<=1 for p in solution['profile'].values())


def test_methods_give_meaningfully_different_predictions():
    m=build_model()
    p={k:solve_stage2(m,k)['profile'] for k in METHODS}
    assert abs(p['UQ']['A']-p['SU']['A']) > 0.10
    assert abs(p['CWQ']['B']-p['LCRQ']['B']) > 0.001


def test_slider_recomputes_flow_and_uses_matching_capacities():
    m=build_model({'E13':1.4,'E3':0.75,'E2':1.2})
    assert m.graph['finish']['C']['capacity']==pytest.approx(81.2)
    assert m.graph['core']['branch']['capacity']==pytest.approx(55.5)
    for method in METHODS:
        r=solve_stage2(m,method)
        assert max(r['errors'].values()) < 3e-5
        assert sum(r['profile'].values()) == pytest.approx(1,abs=1e-8)


def test_zero_capacity_source_edge_zero_flow():
    m=build_model({'E1':0})
    for method in METHODS:
        r=solve_stage2(m,method)
        assert r['max_flow']==pytest.approx(0)
        assert all(v==0 for v in r['profile'].values())


def test_capacity_constraints_under_several_slider_combinations():
    # Deterministic cases, including zero and bottleneck changes.
    for sliders in [
        {'E3':0.0}, {'E7':0.15,'E8':0.2},
        {'E2':2.0,'E9':1.8}, {'E1':0.5,'E13':1.5},
        {'E6':0,'E10':0}, {'E2':1.25,'E4':1.4,'E12':0.7},
    ]:
        m=build_model(sliders)
        for method in METHODS:
            r=solve_stage2(m,method)
            assert max(r['errors'].values()) < 3e-5


def test_slider_invalid_values_rejected():
    for bad in [-0.01,2.01,float('nan'),float('inf')]:
        with pytest.raises(ValueError): build_model({'E1':bad})
    with pytest.raises(ValueError): build_model({'NO_SUCH_EDGE':1.0})


def test_inverse_target_unattainable_with_baseline_but_attainable_after():
    m=build_model()
    F,_=maximum_flow(m)
    # C has exactly one incoming biological edge E13 with capacity 58.
    assert F==pytest.approx(120)
    assert m.graph['finish']['C']['capacity']==pytest.approx(58)
    assert F*OBSERVED_PROFILE['C']==pytest.approx(66)
    closest=closest_baseline(m,OBSERVED_PROFILE)
    assert closest['profile']['C']<=58/F+1e-6
    inv=solve_inverse(m,OBSERVED_PROFILE)
    assert inv['max_flow']==pytest.approx(F)
    for term in TERMINALS:
        assert inv['profile'][term] ==pytest.approx(OBSERVED_PROFILE[term],abs=1e-6)
    assert max(inv['residuals'].values())<3e-5
    assert inv['capacity_after']['E13']==pytest.approx(66,abs=1e-5)
    # This is *globally optimal* since at least an +8 change to E13
    # is necessary and feasible with no other capacity change.
    assert inv['objective']==pytest.approx((8/58)**2,rel=1e-5)
    for name,_,_,orig in BASE_EDGES:
        if name != 'E13':
            assert inv['capacity_after'][name]==pytest.approx(orig,abs=1e-5)


def test_inverse_validation_of_target():
    m=build_model()
    with pytest.raises(ValueError): solve_inverse(m,{'A':.4,'B':.4,'C':.4})
    with pytest.raises(ValueError): solve_inverse(m,{'A':-.1,'B':.6,'C':.5})


def test_inverse_does_not_imply_all_forward_methods_equal_target():
    m=build_model()
    inv=solve_inverse(m,OBSERVED_PROFILE)
    corrected=build_model()
    for u,v,data in corrected.graph.edges(data=True):
        if not data['auxiliary']:
            data['capacity']=inv['capacity_after'][data['id']]
    corrected.capacities[:]=[corrected.graph[u][v]['capacity'] for u,v in corrected.edges]
    for method in METHODS:
        r=solve_stage2(corrected,method)
        assert r['max_flow']==pytest.approx(inv['max_flow'])
        assert abs(r['profile']['C']-OBSERVED_PROFILE['C'])>.05


def test_objective_weights_match_research_formulas():
    m=build_model()
    edges={m.graph[u][v]['id']:i for i,(u,v) in enumerate(m.edges)}
    i=edges['E13']; c=m.capacities[i]
    assert objective_weights(m,'UQ')[i]==pytest.approx(1)
    assert objective_weights(m,'CWQ')[i]==pytest.approx(1/c)
    assert objective_weights(m,'SU')[i]==pytest.approx(1/c**2)
    # from node finish: E12=36, E13=58
    assert objective_weights(m,'LCRQ')[i]==pytest.approx((36+58)/58)


def test_random_slider_settings_deterministic_stress():
    rng=np.random.default_rng(12345)
    for case in range(25):
        values=rng.uniform(0,2,len(BASE_EDGES))
        if case%3==0:
            values[case%len(BASE_EDGES)]=0.0
        model=build_model({f'E{i+1}':float(v) for i,v in enumerate(values)})
        for method in METHODS:
            solution=solve_stage2(model,method)
            assert max(solution['errors'].values()) < 3e-5
