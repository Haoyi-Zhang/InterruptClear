from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from .model import Model, Transition
from .semantics import State, successors, discrete_successor, initial_state, explore

@dataclass(frozen=True, order=True)
class Outcome:
    bad_inside: bool
    taint: bool
    pending: bool
    region: int
    events_used: int
    interrupts_used: int

    def project(self, drop: str | None=None) -> tuple:
        names=("bad_inside","taint","pending","region","events_used","interrupts_used")
        return tuple(getattr(self,n) for n in names if n!=drop)

@dataclass(frozen=True)
class CallKey:
    transition_id: str
    pc: str
    stack: tuple[str,...]
    region: int
    taint: bool
    pending: bool
    bad: bool
    events: int
    interrupts: int


def episode_outcomes(model: Model, call_state: State, call: Transition) -> frozenset[Outcome]:
    entered=discrete_successor(model,call_state,call)
    if entered is None: return frozenset()
    base_depth=len(call_state.stack)
    q=deque([entered]); seen={entered}; outs=set()
    while q:
        s=q.popleft()
        if len(s.stack)==base_depth:
            # matching return has happened; do not continue into the caller.
            outs.add(Outcome(s.bad and not call_state.bad,s.taint,s.pending,s.region,
                             s.events-call_state.events,s.interrupts-call_state.interrupts))
            continue
        for _,ns in successors(model,s):
            if ns not in seen:
                seen.add(ns); q.append(ns)
    return frozenset(outs)


def contract_reachability(model: Model):
    start=initial_state(model); q=deque([start]); seen={start}; pred={start:None}; summaries={}
    while q:
        s=q.popleft()
        # exact time and non-call steps; interrupt steps are replaced by their complete episode relation
        for label,ns in successors(model,s):
            trans=next((t for t in model.transitions if t.id==label),None)
            if trans is not None and trans.event=="interrupt":
                key=CallKey(trans.id,s.pc,s.stack,s.region,s.taint,s.pending,s.bad,s.events,s.interrupts)
                outs=episode_outcomes(model,s,trans); summaries[key]=outs
                for o in sorted(outs):
                    # interrupt episode returns to the designated return location and restores base stack.
                    ns2=State(str(trans.return_pc),s.stack,o.region,o.taint,o.pending,s.bad or o.bad_inside,
                              s.events+o.events_used,s.interrupts+o.interrupts_used)
                    if ns2 not in seen:
                        seen.add(ns2); pred[ns2]=(s,f"summary:{trans.id}"); q.append(ns2)
            else:
                if ns not in seen:
                    seen.add(ns); pred[ns]=(s,label); q.append(ns)
    return seen,pred,summaries


def contract_verdict(model: Model) -> bool:
    states,_,_=contract_reachability(model)
    return not any(s.bad for s in states)


def boundary_projection(states: set[State]) -> set[tuple]:
    return {(s.pc,s.stack,s.region,s.taint,s.pending,s.bad,s.events,s.interrupts) for s in states}


def compare_monolithic_and_contract(model: Model) -> dict:
    mono=explore(model)
    cstates,_,summaries=contract_reachability(model)
    # The contract suppresses internal handler states. Compare caller-boundary states: empty stack only.
    mb={s for s in mono.states if not s.stack}
    cb={s for s in cstates if not s.stack}
    return {
        "model":model.name,
        "monolithic_safe":not mono.unsafe,
        "contract_safe":not any(s.bad for s in cstates),
        "boundary_equal":boundary_projection(mb)==boundary_projection(cb),
        "monolithic_boundary_count":len(mb),
        "contract_boundary_count":len(cb),
        "summary_instances":len(summaries),
    }
