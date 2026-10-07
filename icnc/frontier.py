"""Exact symbolic causal obstructions for every static repair and smaller budget."""
from __future__ import annotations
from collections import deque
from .model import Model, initial_state, successors, _prepare, _successors
from .runtime_limits import check_cpu_limit

class BudgetExceeded(RuntimeError): pass
class Meter:
    def __init__(self,limit=250000): self.limit=limit; self.counts={}
    def charge(self,kind,n=1):
        check_cpu_limit()
        self.counts[kind]=self.counts.get(kind,0)+n
        if sum(self.counts.values())>self.limit: raise BudgetExceeded('campaign obligation ceiling; no verdict')

def minimal_masks(values):
    kept=[]
    for v in sorted(set(values),key=lambda x:(x.bit_count(),x)):
        if not any((x & v)==x for x in kept): kept.append(v)
    return tuple(sorted(kept))

def lower(a,b):
    # a is no harder to admit and cannot be blocked without also blocking b.
    return a[0]&b[0]==a[0] and all(x<=y for x,y in zip(a[1:],b[1:]))

def reduce_frontier(values):
    kept=[]
    for v in sorted(set(values),key=lambda x:(x[0].bit_count(),sum(x[1:]),x)):
        if not any(lower(x,v) for x in kept): kept.append(v)
    return tuple(sorted(kept))

def transfers(m,e,t,p):
    """A term mask F denotes survival iff no chosen repair lies in F."""
    index=m.atom_index
    return _transfers(index,e,t,p)

def _transfers(index,e,t,p):
    def gate(terms,a):
        return minimal_masks(v | (1<<index[a]) for v in terms) if a is not None else terms
    t=gate(t,e.t_clear); p=gate(p,e.p_clear)
    bad=t if e.kind=='use' else ()
    if e.kind=='arm': t=(0,)
    elif e.kind=='neutralize': t=()
    elif e.kind=='schedule': p=(0,)
    elif e.kind=='clear_pending': p=()
    elif e.kind=='commit': t=minimal_masks(t+p); p=()
    return t,p,bad

def build(m:Model,meter:Meter|None=None):
    meter=meter or Meter(); root=initial_state(m)
    structure=_prepare(m)
    seen={root}; todo=deque([root]); graph={}; parent={root:None}
    while todo:
        s=todo.popleft(); arcs=list(_successors(m,s,structure)); graph[s]=arcs
        meter.charge('skeleton_edges',len(arcs))
        for label,z,e in arcs:
            if z not in seen:
                seen.add(z); parent[z]=(s,label); todo.append(z)
                if len(seen)>250000: raise BudgetExceeded('state ceiling')
    rank=m.zero_rank
    order=sorted(seen,key=lambda s:(s[0],rank[s[3]],s[4],s[1],s[2],s[3],s[5]))
    values={s:((),()) for s in seen}; values[root]=((0,) if m.taint else (), (0,) if m.pending else ())
    raw=[]
    for s in order:
        t,p=values[s]
        for label,z,e in graph[s]:
            meter.charge('symbolic_arcs')
            if e is None: nt,np=t,p
            else:
                nt,np,bad=transfers(m,e,t,p) if structure is None else _transfers(structure.atom_index,e,t,p)
                for mask in bad:
                    raw.append((mask,z[0],z[1],z[2])); meter.charge('bad_terms')
            ot,op=values[z]
            values[z]=(minimal_masks(ot+nt),minimal_masks(op+np))
    frontier=reduce_frontier(raw)
    indices={s:i for i,s in enumerate(order)}
    def row(s): return [s[0],s[1],s[2],s[3],s[4],list(s[5])]
    proof=[]
    for s in order:
        par=parent[s]
        proof.append({'state':row(s),'parent':None if par is None else [indices[par[0]],list(par[1])], 't':list(values[s][0]),'p':list(values[s][1])})
    cert={'schema':'neutralization-frontier','model':m.raw(),'nodes':proof,'frontier':[list(x) for x in frontier]}
    return {'frontier':frontier,'certificate':cert,'states':len(seen),'edges':sum(len(a) for a in graph.values()),'raw_bad_terms':len(raw),'proof_terms':sum(len(t)+len(p) for t,p in values.values())}

def unsafe(frontier,plan,cap):
    return any(not (mask&plan) and n<=cap[0] and k<=cap[1] and h<=cap[2] for mask,n,k,h in frontier)

def plan_cost(m,plan): return sum(c for i,(_,c) in enumerate(m.atoms) if plan&(1<<i))

def synthesize(m,frontier,cap):
    feasible=[p for p in range(1<<len(m.atoms)) if not unsafe(frontier,p,cap)]
    if not feasible: return {'minimum_cost':None,'optimal_plans':[],'safe_plans':0}
    c=min(plan_cost(m,p) for p in feasible)
    return {'minimum_cost':c,'optimal_plans':[p for p in feasible if plan_cost(m,p)==c],'safe_plans':len(feasible)}
