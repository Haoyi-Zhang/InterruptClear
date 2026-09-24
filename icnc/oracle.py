from __future__ import annotations
from dataclasses import dataclass, replace
from fractions import Fraction
from collections import deque
from .model import Model, guard_holds, regions

@dataclass(frozen=True,order=True)
class CState:
    pc:str; stack:tuple[str,...]; x:Fraction; taint:bool; pending:bool; bad:bool; events:int; interrupts:int

def representatives(model:Model):
    vals=[]
    cs=model.constants
    for i,c in enumerate(cs):
        vals.append(Fraction(c))
        if i+1<len(cs): vals.append(Fraction(c+cs[i+1],2))
    vals.append(Fraction(cs[-1]+1))
    return tuple(vals)

def _g(x,op,c):
    if op=="true": return True
    return {"<":x<c,"<=":x<=c,"==":x==c,">=":x>=c,">":x>c}[op]

def _inv(m,pc,x):
    op,c=m.invariant(pc); return _g(x,op,c)

def concrete_verdict(model:Model)->bool:
    reps=representatives(model)
    start=CState(model.initial_pc,(),Fraction(0),model.initial_taint,model.initial_pending,False,0,0)
    q=deque([start]); seen={start}
    while q:
        s=q.popleft()
        if s.bad:return False
        nxt=[]
        if s.pc not in model.urgent:
            for y in reps:
                if y>s.x and _inv(model,s.pc,y): nxt.append(replace(s,x=y))
        if s.events<model.max_events:
            for t in model.outgoing(s.pc):
                if not _g(s.x,t.guard_op,t.guard_c): continue
                ta,p,b=s.taint,s.pending,s.bad
                if t.event=="arm":ta=True
                elif t.event=="use":b=b or ta
                elif t.event=="neutralize":ta=False
                elif t.event=="schedule":p=True
                elif t.event=="clear_pending":p=False
                elif t.event=="commit":
                    if p:ta=True;p=False
                stack=s.stack;ints=s.interrupts
                if t.event=="interrupt":
                    if ints>=model.max_interrupts or len(stack)>=model.max_depth:continue
                    stack=stack+(str(t.return_pc),);pc=str(t.target);ints+=1
                elif t.event=="return":
                    if not stack:continue
                    pc=stack[-1];stack=stack[:-1]
                else:pc=str(t.dst)
                x=Fraction(0) if t.reset else s.x
                ns=CState(pc,stack,x,ta,p,b,s.events+1,ints)
                if _inv(model,pc,x):nxt.append(ns)
        for ns in nxt:
            if ns not in seen:seen.add(ns);q.append(ns)
    return True
