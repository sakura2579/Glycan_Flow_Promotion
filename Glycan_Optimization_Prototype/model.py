"""Small-scale educational flow-optimization reference implementation.

Forward objective definitions are based on the supplied IEEM 2026 Forward paper
and Glycan_Flow_Research_Shared source code. Inverse formulation is based on
IEEM 2026 Inverse paper. This *toy* topology derives from the predecessor demo;
its capacities and 'observed' profile are synthetic, not experimental TPM/glycomics.

Dependencies: numpy, scipy, networkx. No cvxpy required for this self-contained
reference, but this SLSQP backend must be revalidated against CVXPY/CLARABEL
or OSQP before claiming numerical equivalence in a research publication.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

import networkx as nx
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, minimize

TERMINALS = ("A", "B", "C")
METHODS = ("UQ", "CWQ", "SU", "LCRQ")
SUPPLY = 120.0
# Synthetic demo capacities: consistent with the predecessor website's
# edge topology and base edge values. No association with RNA TPM data.
BASE_EDGES = (
    ("E1", "input", "core", 120.0),
    ("E2", "core", "high", 46.0),
    ("E3", "core", "branch", 74.0),
    ("E4", "core", "stall", 34.0),
    ("E5", "high", "branch", 44.0),
    ("E6", "high", "A", 42.0),
    ("E7", "branch", "extend", 58.0),
    ("E8", "branch", "finish", 38.0),
    ("E9", "stall", "finish", 40.0),
    ("E10", "extend", "A", 26.0),
    ("E11", "extend", "B", 60.0),
    ("E12", "finish", "B", 36.0),
    ("E13", "finish", "C", 58.0),
)
# Deliberately unattainable without changing some baseline capacities:
# C needs 66 (=55% of 120) but the only incoming edge E13 has capacity 58.
OBSERVED_PROFILE = {"A": 0.25, "B": 0.20, "C": 0.55}
TOL = 3e-5


@dataclass
class Model:
    graph: nx.DiGraph
    edges: list[tuple[str, str]]
    capacities: np.ndarray
    biological_indices: list[int]
    terminal_indices: dict[str, int]
    incidence: np.ndarray  # outflow - inflow per node (excluding source and sink)
    incidence_nodes: list[str]
    source_row: np.ndarray
    sink_row: np.ndarray
    baseline_cut_mask: np.ndarray

    def flow_to_map(self, flows: np.ndarray) -> dict[str, float]:
        return {f"{u}->{v}": float(flows[i]) for i, (u, v) in enumerate(self.edges)}


def build_model(capacity_multipliers: dict[str, float] | None = None) -> Model:
    """Create a DAG with synthetic source/sink and fixed supply cap 120.

    Sliders change each biological capacity to original_capacity*multiplier,
    0<=multiplier<=2. Source/sink artificial arcs are not slider-adjustable.
    """
    capacity_multipliers = capacity_multipliers or {}
    invalid = set(capacity_multipliers) - {x[0] for x in BASE_EDGES}
    if invalid:
        raise ValueError(f"Unknown edge labels: {sorted(invalid)}")
    graph = nx.DiGraph()
    graph.add_edge("s", "input", capacity=SUPPLY, id="supply", auxiliary=True)
    for edge_id, start, end, base in BASE_EDGES:
        factor = float(capacity_multipliers.get(edge_id, 1.0))
        if not math.isfinite(factor) or not 0 <= factor <= 2:
            raise ValueError(f"{edge_id}: slider factor must be in [0,2]")
        graph.add_edge(start, end, capacity=base * factor, id=edge_id, auxiliary=False)
    for term in TERMINALS:
        graph.add_edge(term, "t", capacity=float("inf"), id=f"sink_{term}", auxiliary=True)
    edges = list(graph.edges())
    caps = np.array([graph[u][v]["capacity"] for u, v in edges], dtype=float)
    biologic = [i for i, e in enumerate(edges) if not graph[e[0]][e[1]]["auxiliary"]]
    terminal_indices = {t: edges.index((t, "t")) for t in TERMINALS}
    nodes = [n for n in graph.nodes() if n not in ("s", "t")]
    inc = np.array([[float(u == n) - float(v == n) for u, v in edges] for n in nodes])
    src = np.array([float(u == "s") - float(v == "s") for u, v in edges])
    sink = np.array([float(u == "t") - float(v == "t") for u, v in edges])
    # The singleton {s} is a verified baseline min-cut: only arc s->input has
    # capacity SUPPLY. The cut's capacity is unchanged under inverse changes.
    baseline_cut_mask = np.array([float(u == "s" and v != "s") for u, v in edges])
    return Model(graph, edges, caps, biologic, terminal_indices, inc, nodes, src, sink, baseline_cut_mask)


def maximum_flow(model: Model) -> tuple[float, np.ndarray]:
    value, flow_dict = nx.maximum_flow(model.graph, "s", "t", capacity="capacity")
    x = np.array([flow_dict[u][v] for u, v in model.edges], dtype=float)
    return float(value), x


def constraints(model: Model, value: float) -> tuple[np.ndarray, np.ndarray]:
    # Equality constraints: conservation, source flow and sink flow.
    # Sink balance is implied by conservation at all internal nodes plus source.
    # Omitting that redundant row keeps SLSQP equality constraints full rank.
    A = np.vstack((model.incidence, model.source_row))
    b = np.array([0.0] * len(model.incidence_nodes) + [value])
    return A, b


def finite_bounds(model: Model) -> tuple[np.ndarray, np.ndarray]:
    # Inf only on terminal->t artificial edges; finite bound can be replaced
    # by any value above max supply without changing the feasible flow region.
    high = np.where(np.isfinite(model.capacities), model.capacities, SUPPLY * 10)
    return np.zeros(len(model.edges)), high


def objective_weights(model: Model, method: str) -> np.ndarray:
    if method not in METHODS:
        raise ValueError(f"Unknown forward method: {method}")
    caps = model.capacities
    active = np.flatnonzero(np.isfinite(caps) & (caps > 0))
    w = np.zeros(len(caps))
    if method == "UQ":
        w[active] = 1.0
    elif method == "CWQ":
        w[active] = 1.0 / np.maximum(caps[active], 1e-12)
    elif method == "SU":
        w[active] = 1.0 / np.maximum(caps[active], 1e-12) ** 2
    else:
        out_sums: dict[str, float] = {}
        for i in active:
            start = model.edges[i][0]
            out_sums[start] = out_sums.get(start, 0) + float(caps[i])
        for i in active:
            start = model.edges[i][0]
            ratio = float(caps[i]) / out_sums[start]
            w[i] = 1.0 / max(ratio, 1e-12)
    return w


def validate(model: Model, flows: np.ndarray, value: float, *, atol=TOL) -> dict[str, float]:
    A, b = constraints(model, value)
    effective_upper = np.where(np.isfinite(model.capacities), model.capacities, SUPPLY * 10)
    errors = {
        "nonnegative": float(max(0, -np.min(flows))),
        "capacity": float(max(0, np.max(flows - effective_upper))),
        "conservation_and_total": float(np.max(np.abs(A @ flows - b))),
        "terminal_total": float(abs(sum(flows[i] for i in model.terminal_indices.values()) - value)),
    }
    if not np.isfinite(flows).all() or any(v > atol for v in errors.values()):
        raise AssertionError(f"Invalid flow: {errors}")
    return errors


def terminal_profile(model: Model, x: np.ndarray, total: float) -> dict[str, float]:
    return {t: float(x[i] / total) if total > 1e-12 else 0.0 for t,i in model.terminal_indices.items()}


def solve_stage2(model: Model, method: str) -> dict[str, Any]:
    F, feasible = maximum_flow(model)
    if F <= 1e-10:
        zeros = np.zeros(len(model.edges))
        return {"method":method, "max_flow":0.0,"flows":model.flow_to_map(zeros),
                "profile":terminal_profile(model,zeros,0.0),"solver":"zero-flow", "errors": validate(model,zeros,0.0)}
    A, b = constraints(model, F)
    low, high = finite_bounds(model)
    weights = objective_weights(model, method)
    # Scale Hessian by its max weight to aid conditioning; minimizer unaffected.
    w = weights / max(1.0, np.max(weights))
    def fn(x): return float(np.dot(w, x*x))
    def jac(x): return 2*w*x
    res = minimize(fn, feasible, jac=jac, method="SLSQP",bounds=Bounds(low,high),
                   constraints=[LinearConstraint(A,b,b)],
                   options={"maxiter":2000,"ftol":1e-9})
    solver='scipy.SLSQP'
    if not res.success:
        # SLSQP's line search can stall on zero-capacity arcs or tight cuts;
        # the small-scale convex QP has a smooth analytic Hessian.
        res = minimize(fn, feasible, jac=jac, hess=lambda x: np.diag(2*w),
                       method='trust-constr', bounds=Bounds(low,high),
                       constraints=[LinearConstraint(A,b,b)],
                       options={'maxiter':1000,'gtol':1e-8,'xtol':1e-10,'barrier_tol':1e-10})
        solver='scipy.trust-constr'
    if not res.success:
        raise RuntimeError(f"Stage2 {method} solver error: {res.message}")
    errs = validate(model,res.x,F)
    return {"method":method,"max_flow":F,"flows":model.flow_to_map(res.x),
            "profile":terminal_profile(model,res.x,F), "solver":solver, "errors":errs,
            "objective":float(np.dot(weights,res.x**2))}


def closest_baseline(model: Model, target: dict[str, float]) -> dict[str, Any]:
    """Paper-like comparison: best-matching *baseline* maximum-flow profile.

    This is NOT the same as one of the four Forward allocation objectives.
    """
    F, x0 = maximum_flow(model)
    A,b=constraints(model,F)
    low,high=finite_bounds(model)
    def fn(x):
        p=np.array([x[model.terminal_indices[t]]/F for t in TERMINALS])
        goal=np.array([target[t] for t in TERMINALS])
        return float(np.sum((p-goal)**2))
    def jac(x):
        grad=np.zeros(len(x))
        for t in TERMINALS:
            i=model.terminal_indices[t]
            grad[i]=2*(x[i]/F-target[t])/F
        return grad
    res=minimize(fn,x0,jac=jac,method='SLSQP',bounds=Bounds(low,high),
                 constraints=[LinearConstraint(A,b,b)],options={'ftol':1e-12,'maxiter':1500})
    if not res.success: raise RuntimeError(f"Closest baseline failed: {res.message}")
    errors=validate(model,res.x,F)
    return {'max_flow':F, 'profile':terminal_profile(model,res.x,F),
            'flows':model.flow_to_map(res.x),'errors':errors,
            'squared_profile_error':fn(res.x)}


def solve_inverse(model: Model, target: dict[str,float]) -> dict[str, Any]:
    """Inverse convex QP: minimize sum[(c'_e-c_e)/max(c_e,eps)]^2.

    Constraints include: flow conservation, terminal target f_i=F q_i,
    flow <= corrected capacities for biological edges, nonnegative caps,
    unchanged auxiliary capacities, and fixed baseline min-cut capacity.
    Here the fixed singleton source cut ensures corrected max flow remains F.
    For this example, fixed F is a deliberate paper-compatible restriction
    (the paper uses F>=F_base with a baseline min-cut certificate).
    """
    if set(target)!=set(TERMINALS) or any(not math.isfinite(float(v)) or v<0 for v in target.values()) or abs(sum(target.values())-1)>1e-10:
        raise ValueError('target must be a three-terminal probability distribution')
    F,_ = maximum_flow(model)
    # For this topology the singleton {s} cut is a baseline minimum cut.
    cut=float(np.sum(model.capacities[model.baseline_cut_mask > 0]))
    if abs(cut-F)>1e-8:
        raise ValueError(f'fixed source cut is not a baseline mincut: cut={cut} F={F}')
    n=len(model.edges)
    bio=np.array(model.biological_indices,dtype=int)
    orig=model.capacities[bio]
    k=len(bio)
    A_flow,b_flow=constraints(model,F)
    Aeq=np.block([[A_flow,np.zeros((A_flow.shape[0],k))]])
    beq=b_flow.copy()
    terminal_eq=np.zeros((len(TERMINALS),n+k))
    for row,term in enumerate(TERMINALS): terminal_eq[row,model.terminal_indices[term]]=1.0
    Aeq=np.vstack((Aeq,terminal_eq))
    beq=np.concatenate((beq,[F*target[t] for t in TERMINALS]))
    # Baseline min-cut capacity certificate: sum c'_edge on s-side = F.
    # All arcs on this cut are auxiliary/fixed in this demonstrator.
    cut_eq=np.zeros((1,n+k))
    Aeq=np.vstack((Aeq,cut_eq)) if False else Aeq  # fixed cut already certified
    # f_e <= c'_e for editable biological edges; remaining f_e <= original cap.
    Aub=np.zeros((k,n+k))
    for j,i in enumerate(bio): Aub[j,i]=1.0; Aub[j,n+j]=-1.0
    cap_high=np.where(np.isfinite(model.capacities),model.capacities,SUPPLY*10)
    bounds=[(0,float(cap_high[i])) if i not in bio else (0,None) for i in range(n)]+[(0,None)]*k
    # LP warm-start: minimize the L1 sum of relative capacity changes.
    # A pure zero-cost feasibility LP can return an extreme point with huge
    # and unnecessary changes, at which SLSQP tends to stagnate.
    denominators=np.maximum(orig,1e-6)
    # y=(flows, corrected capacities, relative absolute deviation variables)
    lp_dim=n+2*k
    lp_Aeq=np.pad(Aeq,((0,0),(0,k)))
    lp_Aub=np.zeros((3*k,lp_dim))
    lp_Aub[:k,:n+k]=Aub
    lp_bub=np.zeros(3*k)
    for j in range(k):
        #  (c'_j - orig_j) / denom_j <= d_j
        lp_Aub[k+j,n+j]=1/denominators[j]
        lp_Aub[k+j,n+k+j]=-1
        lp_bub[k+j]=orig[j]/denominators[j]
        # -(c'_j - orig_j) / denom_j <= d_j
        lp_Aub[2*k+j,n+j]=-1/denominators[j]
        lp_Aub[2*k+j,n+k+j]=-1
        lp_bub[2*k+j]=-orig[j]/denominators[j]
    lp_obj=np.zeros(lp_dim)
    lp_obj[n+k:]=1
    lp_bounds=bounds+[(0,None)]*k
    lp=linprog(lp_obj,A_ub=lp_Aub,b_ub=lp_bub,A_eq=lp_Aeq,b_eq=beq,bounds=lp_bounds,method='highs')
    if not lp.success: raise RuntimeError(f'Inverse target infeasible: {lp.message}')
    denominators=np.maximum(orig,1e-6)
    # Multiplying objective by a constant is safe and improves scaling.
    def fn(x):
        return float(np.sum(((x[n:]-orig)/denominators)**2))
    def jac(x):
        out=np.zeros(n+k);out[n:]=2*(x[n:]-orig)/(denominators**2);return out
    cons=[LinearConstraint(Aeq,beq,beq),LinearConstraint(Aub,-np.inf,np.zeros(k))]
    result=minimize(fn,lp.x[:n+k],method='SLSQP',jac=jac,
                   bounds=Bounds([z[0] if z[0] is not None else -np.inf for z in bounds],
                                 [z[1] if z[1] is not None else np.inf for z in bounds]),
                   constraints=cons,options={'ftol':1e-11,'maxiter':4000})
    if not result.success: raise RuntimeError(f'Inverse solver error: {result.message}')
    x=result.x[:n]; c=result.x[n:]
    residual_eq=float(np.max(np.abs(Aeq@result.x-beq)))
    residual_capacity=float(max(0,np.max(Aub@result.x)))
    if residual_eq>TOL or residual_capacity>TOL: raise AssertionError('Inverse constraints failed')
    # Multipliers might exceed 2 in the unconstrained inverse. Build the
    # corrected graph directly, rather than using the Forward UI slider bounds.
    corrected_graph=model.graph.copy()
    for j,i in enumerate(bio):
        u,v=model.edges[i]; corrected_graph[u][v]['capacity']=float(c[j])
    new_F=nx.maximum_flow_value(corrected_graph,'s','t',capacity='capacity')
    if abs(new_F-F)>TOL: raise AssertionError(f'Inverse did not maintain max flow: {new_F} vs {F}')
    residuals={"flow_conservation_and_profile":residual_eq,"capacity":residual_capacity,
               "maximum_flow":abs(new_F-F),"observed_profile":max(abs(x[model.terminal_indices[t]]/F-target[t]) for t in TERMINALS)}
    return {"max_flow":F,"target":dict(target),"profile":terminal_profile(model,x,F),
            "capacity_before":{edge_id:base for edge_id,_,_,base in BASE_EDGES},
            "capacity_after":{edge_id:float(c[j]) for j,(edge_id,_,_,_) in enumerate(BASE_EDGES)},
            "flows":model.flow_to_map(x),"solver":"scipy.SLSQP","objective":fn(result.x),
            "residuals":residuals,"corrected_graph":corrected_graph}


def find_differences(a:dict[str,float],b:dict[str,float])->dict[str,float]:
    return {t:float(a[t]-b[t]) for t in TERMINALS}
