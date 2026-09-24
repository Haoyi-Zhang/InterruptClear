from __future__ import annotations
from dataclasses import dataclass, replace
from collections import deque
from typing import Iterable
from .model import Model, Transition, Region, regions, guard_holds, invariant_holds

@dataclass(frozen=True, order=True)
class State:
    pc: str
    stack: tuple[str,...]
    region: int
    taint: bool
    pending: bool
    bad: bool
    events: int
    interrupts: int

@dataclass(frozen=True)
class Edge:
    src: State
    label: str
    dst: State

@dataclass
class Reachability:
    states: set[State]
    edges: set[Edge]
    predecessors: dict[State, tuple[State,str] | None]

    @property
    def unsafe(self) -> bool:
        return any(s.bad for s in self.states)

    def shortest_bad_trace(self) -> list[tuple[str,State]]:
        bads=[s for s in self.states if s.bad]
        if not bads: return []
        target=min(bads,key=lambda s:(s.events+s.interrupts,len(s.stack),s))
        rev=[]
        cur=target
        while self.predecessors[cur] is not None:
            prev,label=self.predecessors[cur]
            rev.append((label,cur)); cur=prev
        rev.append(("initial",cur))
        return list(reversed(rev))


def initial_state(model: Model) -> State:
    rs=regions(model)
    idx=next(i for i,r in enumerate(rs) if r.kind=="point" and r.lo==0)
    s=State(model.initial_pc,(),idx,model.initial_taint,model.initial_pending,False,0,0)
    if not invariant_holds(model,s.pc,rs[s.region]): raise ValueError("initial invariant violated")
    return s


def time_successors(model: Model, s: State) -> Iterable[tuple[str,State]]:
    if s.pc in model.urgent: return ()
    rs=regions(model)
    out=[]
    # zero delay is semantically available but omitted because it is a self-loop.
    j=s.region+1
    if j < len(rs) and invariant_holds(model,s.pc,rs[j]):
        out.append((f"delay->{rs[j].label()}", replace(s,region=j)))
    return tuple(out)


def _apply_action(s: State, event: str) -> tuple[bool,bool,bool]:
    taint,pending,bad=s.taint,s.pending,s.bad
    if event=="arm": taint=True
    elif event=="use": bad=bad or taint
    elif event=="neutralize": taint=False
    elif event=="schedule": pending=True
    elif event=="clear_pending": pending=False
    elif event=="commit":
        if pending: taint=True; pending=False
    return taint,pending,bad


def discrete_successor(model: Model, s: State, t: Transition) -> State | None:
    if s.events >= model.max_events or t.src != s.pc: return None
    rs=regions(model); r=rs[s.region]
    if not guard_holds(r,t.guard_op,t.guard_c): return None
    nregion=next(i for i,x in enumerate(rs) if x.kind=="point" and x.lo==0) if t.reset else s.region
    taint,pending,bad=_apply_action(s,t.event)
    stack=s.stack; interrupts=s.interrupts
    if t.event=="interrupt":
        if interrupts >= model.max_interrupts or len(stack) >= model.max_depth: return None
        stack=stack+(str(t.return_pc),); pc=str(t.target); interrupts+=1
    elif t.event=="return":
        if not stack: return None
        pc=stack[-1]; stack=stack[:-1]
    else:
        pc=str(t.dst)
    ns=State(pc,stack,nregion,taint,pending,bad,s.events+1,interrupts)
    if not invariant_holds(model,ns.pc,rs[ns.region]): return None
    return ns


def successors(model: Model, s: State) -> tuple[tuple[str,State],...]:
    out=list(time_successors(model,s))
    for t in model.outgoing(s.pc):
        ns=discrete_successor(model,s,t)
        if ns is not None: out.append((t.id,ns))
    out.sort(key=lambda x:(x[0],x[1]))
    return tuple(out)


def explore(model: Model, start: State | None=None, stop_at: callable | None=None) -> Reachability:
    start=initial_state(model) if start is None else start
    q=deque([start]); seen={start}; edges=set(); pred={start:None}
    while q:
        s=q.popleft()
        if stop_at is not None and stop_at(s,start):
            continue
        for label,ns in successors(model,s):
            e=Edge(s,label,ns); edges.add(e)
            if ns not in seen:
                seen.add(ns); pred[ns]=(s,label); q.append(ns)
    return Reachability(seen,edges,pred)


def safety_verdict(model: Model) -> bool:
    return not explore(model).unsafe
