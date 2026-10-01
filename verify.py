"""Independent implementation of the declarative model and certificate checker.

Independence means separate source logic, not independent authorship or a
machine-checked proof. Invoker-supplied model and bounds are trusted inputs.
"""
from __future__ import annotations
import json
from pathlib import Path

WORK_TOTAL = 0

class Rejected(ValueError):pass

def require(ok:bool,why:str):
    if not ok:raise Rejected(why)

def read_json(path,limit):
    p=Path(path)
    require(p.stat().st_size<=limit,'file size')
    data=p.read_bytes();require(len(data)<=limit,'file size')
    def pairs(xs):
        d={}
        for k,v in xs:
            require(k not in d,'duplicate JSON key');d[k]=v
        return d
    def invalid(_):raise Rejected('nonfinite JSON')
    try:return json.loads(data,object_pairs_hook=pairs,parse_constant=invalid)
    except (UnicodeError,json.JSONDecodeError,RecursionError) as e:raise Rejected('invalid JSON') from e

def checked_model(m):
    require(type(m) is dict and set(m)=={'id','title','initial','nodes','edges'},'model keys')
    for key in ('id','title','initial'):require(type(m[key]) is str and 0<len(m[key])<=200,'model identifier')
    require(type(m['nodes']) is list and 1<=len(m['nodes'])<=48,'location cap')
    ns={}
    for v in m['nodes']:
        require(type(v) is dict and set(v)=={'id','clean','pending'},'node fields')
        require(type(v['id']) is str and 0<len(v['id'])<=64 and v['id'] not in ns,'node identifier')
        require(type(v['clean']) is bool and type(v['pending']) is bool,'predicate type');ns[v['id']]=v
    require(m['initial'] in ns,'initial')
    require(type(m['edges']) is list and len(m['edges'])<=128,'transition cap')
    es={};M=0
    for t in m['edges']:
        require(type(t) is dict and set(t)=={'id','src','dst','kind','guard','reset'},'edge fields')
        require(type(t['id']) is str and 0<len(t['id'])<=64 and t['id'] not in es,'edge identifier')
        require(type(t['src']) is str and t['src'] in ns and type(t['dst']) is str and t['dst'] in ns,'edge endpoint')
        require(type(t['kind']) is str and t['kind'] in {'step','use','interrupt','neutralize','effect'},'edge kind')
        require(type(t['reset']) is bool,'reset type')
        require(type(t['guard']) is list and len(t['guard'])<=8,'guard size')
        for atom in t['guard']:
            require(type(atom) is list and len(atom)==2,'guard atom')
            require(type(atom[0]) is str and atom[0] in {'<','<=','==','>=','>'},'guard operation')
            require(type(atom[1]) is int and 0<=atom[1]<=256,'guard constant');M=max(M,atom[1])
        if t['kind']=='neutralize':require(ns[t['dst']]['clean'],'neutralization postcondition')
        es[t['id']]=t
    return ns,es,M

def truth(guard,twice_value):
    # Integer arithmetic only; no calls to the generator's Fraction evaluator.
    for op,c in guard:
        v=2*c
        if op=='<' and not twice_value<v:return False
        if op=='<=' and not twice_value<=v:return False
        if op=='==' and not twice_value==v:return False
        if op=='>=' and not twice_value>=v:return False
        if op=='>' and not twice_value>v:return False
    return True

def check(m,c,events,interrupts):
    global WORK_TOTAL
    require(type(events) is int and 0<=events<=32 and type(interrupts) is int and 0<=interrupts<=8,'requested bounds')
    ns,es,M=checked_model(m)
    require(type(c) is dict,'certificate object')
    require(c.get('kind') in ('safety','diagnostic'),'certificate kind')
    extra='states' if c['kind']=='safety' else 'steps'
    require(set(c)=={'kind','model','events','interrupts',extra},'certificate fields')
    require(type(c['model']) is str and c['model']==m['id'],'model identifier mismatch')
    require(type(c['events']) is int and c['events']==events and type(c['interrupts']) is int and c['interrupts']==interrupts,'bound mismatch')
    count=0
    if c['kind']=='diagnostic':
        require(type(c['steps']) is list and 0<len(c['steps'])<=events,'diagnostic length')
        q=m['initial'];clock=0;k=0;found=False
        for st in c['steps']:
            require(type(st) is dict and set(st)=={'edge','x2'},'step fields')
            require(type(st['edge']) is str and st['edge'] in es,'step edge')
            t=es[st['edge']];v=st['x2']
            require(type(v) is int and 0<=v<=2*M+2,'diagnostic time')
            require(t['src']==q and v>=clock and truth(t['guard'],v),'infeasible diagnostic')
            k+=int(t['kind']=='interrupt');require(k<=interrupts,'diagnostic interrupt bound')
            if t['kind']=='use' and not ns[q]['clean']:found=True
            q=t['dst'];clock=0 if t['reset'] else v;count+=1;WORK_TOTAL+=1
        require(found,'no bad protected use')
        return {'verdict':'UNSAFE','obligations':count}
    require(type(c['states']) is list and 0<len(c['states'])<=250000,'certificate state cap')
    S=set()
    for row in c['states']:
        require(type(row) is list and len(row)==4,'state shape')
        n,k,q,r=row
        require(type(n) is int and 0<=n<=events and type(k) is int and 0<=k<=min(n,interrupts),'state budgets')
        require(type(q) is str and q in ns and type(r) is int and 0<=r<=2*M+1,'state value')
        t=tuple(row);require(t not in S,'duplicate state');S.add(t)
    require((0,0,m['initial'],0) in S,'initial coverage')
    for n,k,q,r in S:
        if n==events:continue
        for t in es.values():
            if t['src']!=q:continue
            j=k+int(t['kind']=='interrupt')
            if j>interrupts:continue
            # Region ordering is rebuilt from the trusted model, not a supplied edge list.
            for delayed in range(r,2*M+2):
                if not truth(t['guard'],delayed):continue
                count+=1;WORK_TOTAL+=1;require(count<=500000,'checker obligation cap')
                require(t['kind']!='use' or ns[q]['clean'],'bad protected use')
                dst=(n+1,j,t['dst'],0 if t['reset'] else delayed)
                require(dst in S,'successor coverage')
    return {'verdict':'SAFE','obligations':count}

if __name__=='__main__':
    import argparse,sys
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model');p.add_argument('certificate');p.add_argument('--events',type=int,required=True);p.add_argument('--interrupts',type=int,required=True)
    a=p.parse_args()
    try:result=check(read_json(a.model,262144),read_json(a.certificate,16777216),a.events,a.interrupts)
    except (Rejected,OSError,TypeError,KeyError) as e:print('REJECTED:',str(e));sys.exit(2)
    print(json.dumps(result,sort_keys=True))
