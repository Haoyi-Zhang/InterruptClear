"""Explicit-state baseline for a fixed plan. No symbolic frontier operations."""
from collections import deque
from .model import initial_state,successors

def explore(m,plan,meter=None):
    if type(plan) is not int or not 0<=plan<(1<<len(m.atoms)): raise ValueError('plan')
    root=(*initial_state(m),m.taint,m.pending)
    seen={root}; todo=deque([root]); bad_costs=set(); first=None; parents={root:None}; structural_edges=set()
    while todo:
        s=todo.popleft(); base=s[:6]; t,p=s[6:]
        for label,z,e in successors(m,base):
            if meter: meter.charge('explicit_edges')
            structural_edges.add((base,label,z))
            nt,np=t,p
            if e is not None:
                ai=m.atom_index
                if e.t_clear is not None and plan&(1<<ai[e.t_clear]): nt=False
                if e.p_clear is not None and plan&(1<<ai[e.p_clear]): np=False
                if e.kind=='use' and nt:
                    bad_costs.add(z[:3])
                    if first is None:
                        rows=[(label,z)]; cur=s
                        while parents[cur] is not None:
                            prev,lab=parents[cur]; rows.append((lab,cur[:6])); cur=prev
                        first=list(reversed(rows))
                if e.kind=='arm': nt=True
                elif e.kind=='neutralize': nt=False
                elif e.kind=='schedule': np=True
                elif e.kind=='clear_pending': np=False
                elif e.kind=='commit': nt=nt or np; np=False
            dest=(*z,nt,np)
            if dest not in seen: seen.add(dest); parents[dest]=(s,label); todo.append(dest)
    return {'safe':not bad_costs,'bad_costs':bad_costs,'states':len(seen),'reachable':seen,'structural_states':{s[:6] for s in seen},'structural_edges':structural_edges,'witness':first}
