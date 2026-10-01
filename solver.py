"""Exact, bounded, one-clock region exploration of owned declarative automata.

This module is not imported by verify.py or oracle.py. No device operations,
network calls, dynamically evaluated guards, or external solver are used.
"""
from __future__ import annotations
import json
from fractions import Fraction
from pathlib import Path
from collections import deque
from typing import Any

OPS = {'<','<=','==','>=','>'}
KINDS = {'step','interrupt','neutralize','effect','use'}

def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('duplicate JSON key')
        out[k]=v
    return out

def load(path: str | Path) -> dict[str,Any]:
    data=Path(path).read_bytes()
    if len(data)>262144: raise ValueError('model exceeds input limit')
    m=json.loads(data,object_pairs_hook=_pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if not isinstance(m,dict) or set(m)!={'id','title','initial','nodes','edges'}:raise ValueError('model keys')
    if not all(isinstance(m[k],str) and 0<len(m[k])<=200 for k in ['id','title','initial']):raise ValueError('model strings')
    if not isinstance(m['nodes'],list) or not 1<=len(m['nodes'])<=48:raise ValueError('locations')
    nodes={}
    for n in m['nodes']:
        if not isinstance(n,dict) or set(n)!={'id','clean','pending'}:raise ValueError('node keys')
        if not isinstance(n['id'],str) or not 1<=len(n['id'])<=64 or n['id'] in nodes:raise ValueError('node id')
        if type(n['clean']) is not bool or type(n['pending']) is not bool:raise ValueError('node predicates')
        nodes[n['id']]=n
    if m['initial'] not in nodes:raise ValueError('initial location')
    if not isinstance(m['edges'],list) or len(m['edges'])>128:raise ValueError('edges')
    ids=set()
    for e in m['edges']:
        if not isinstance(e,dict) or set(e)!={'id','src','dst','kind','guard','reset'}:raise ValueError('edge keys')
        if not isinstance(e['id'],str) or not 1<=len(e['id'])<=64 or e['id'] in ids:raise ValueError('edge id')
        ids.add(e['id'])
        if e['src'] not in nodes or e['dst'] not in nodes or e['kind'] not in KINDS:raise ValueError('edge references')
        if type(e['reset']) is not bool:raise ValueError('reset')
        if not isinstance(e['guard'],list) or len(e['guard'])>8:raise ValueError('guard length')
        for atom in e['guard']:
            if not isinstance(atom,list) or len(atom)!=2 or atom[0] not in OPS or type(atom[1]) is not int or not 0<=atom[1]<=256:raise ValueError('guard atom')
        if e['kind']=='neutralize' and not nodes[e['dst']]['clean']:raise ValueError('neutralize must establish clean')
    return m

def maximum(m):return max([c for e in m['edges'] for _,c in e['guard']]+[0])

def holds(guard,x:Fraction)->bool:
    for op,c in guard:
        ok={'<':x<c,'<=':x<=c,'==':x==c,'>=':x>=c,'>':x>c}[op]
        if not ok:return False
    return True

def explore(m:dict,events:int,interrupts:int,integer_only:bool=False):
    if type(events) is not int or not 0<=events<=32 or type(interrupts) is not int or not 0<=interrupts<=8:raise ValueError('bounds')
    M=maximum(m); last=2*M+1
    nodes={n['id']:n for n in m['nodes']};adj={q:[] for q in nodes}
    for e in m['edges']:adj[e['src']].append(e)
    root=(0,0,m['initial'],0);seen={root};queue=deque([root]);parent={root:None};witness=None;obligations=0
    while queue:
        st=queue.popleft();n,k,q,r=st
        if n==events:continue
        for e in adj[q]:
            nk=k+(e['kind']=='interrupt')
            if nk>interrupts:continue
            choices=list(range(r,last+1))
            if integer_only:
                # Tail stands for an integer strictly greater than M.
                choices=[s for s in choices if s%2==0 or s==last]
            for s in choices:
                x=Fraction(M+1) if integer_only and s==last else Fraction(s,2)
                if not holds(e['guard'],x):continue
                obligations+=1
                if obligations>500000:raise RuntimeError('obligation cap exceeded')
                dest=(n+1,nk,e['dst'],0 if e['reset'] else s)
                step={'edge':e['id'],'x2':2*x.numerator//x.denominator}
                if e['kind']=='use' and not nodes[q]['clean'] and witness is None:
                    steps=[step];walk=st
                    while parent[walk] is not None:
                        prev,ev=parent[walk];steps.append(ev);walk=prev
                    witness=list(reversed(steps))
                if dest not in seen:
                    seen.add(dest)
                    if len(seen)>250000:raise RuntimeError('state cap exceeded')
                    parent[dest]=(st,step);queue.append(dest)
    if witness is None:
        cert={'kind':'safety','model':m['id'],'events':events,'interrupts':interrupts,'states':[list(s) for s in sorted(seen)]}
    else:cert={'kind':'diagnostic','model':m['id'],'events':events,'interrupts':interrupts,'steps':witness}
    return {'safe':witness is None,'states':len(seen),'obligations':obligations,'certificate':cert,'reachable':seen}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model');p.add_argument('output');p.add_argument('--events',type=int,required=True);p.add_argument('--interrupts',type=int,required=True)
    a=p.parse_args();r=explore(load(a.model),a.events,a.interrupts);Path(a.output).write_text(json.dumps(r['certificate'],separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in r.items() if k not in {'certificate','reachable'}}))
