"""Closed one-clock models; optional pre-edge bit clears do not change admission."""
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
import json, unicodedata
from types import MappingProxyType

OPS = {'<','<=','==','>=','>'}
ACTIONS = {'nop','arm','neutralize','schedule','clear_pending','commit','use','interrupt','return','repair'}

class InvalidModel(ValueError): pass

def identifier(x):
    if type(x) is not str or not x or len(x)>96: raise InvalidModel('nonempty string identifier required')
    normalized=unicodedata.normalize('NFC',x)
    if not normalized or len(normalized)>96: raise InvalidModel('normalized identifier length')
    return normalized

def integer(x,hi):
    if type(x) is not int or not 0<=x<=hi: raise InvalidModel('integer outside admitted range')
    return x

def unique_pairs(rows):
    out={}
    for k,v in rows:
        k=unicodedata.normalize('NFC',k)
        if k in out: raise InvalidModel('duplicate normalized JSON key')
        out[k]=v
    return out

def read(path):
    raw=Path(path).read_bytes()
    if len(raw)>2**20: raise InvalidModel('model byte limit')
    return json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=lambda x: (_ for _ in ()).throw(InvalidModel('nonfinite JSON')))

@dataclass(frozen=True)
class Edge:
    id:str; src:str; dst:str|None; kind:str; guard:tuple; reset:bool; resume:str|None; t_clear:str|None; p_clear:str|None

@dataclass(frozen=True)
class Model:
    name:str; pcs:tuple; initial:str; taint:bool; pending:bool; constants:tuple; urgent:frozenset; invariants:tuple; atoms:tuple; edges:tuple; cap:tuple
    def raw(self):
        return {'name':self.name,'locations':list(self.pcs),'initial':{'pc':self.initial,'taint':self.taint,'pending':self.pending},'constants':list(self.constants),'urgent':sorted(self.urgent),'invariants':{q:[list(a) for a in g] for q,g in self.invariants},'atoms':[{'id':a,'cost':c} for a,c in self.atoms],'edges':[{'id':e.id,'src':e.src,'dst':e.dst,'kind':e.kind,'guard':[list(a) for a in e.guard],'reset':e.reset,'resume':e.resume,'t_clear':e.t_clear,'p_clear':e.p_clear} for e in self.edges],'cap':list(self.cap)}
    def bounded(self,cap):
        cap=tuple(cap)
        if len(cap)!=3: raise InvalidModel('three budget coordinates required')
        for v,h in zip(cap,(32,8,8)): integer(v,h)
        return replace(self,cap=cap)
    @property
    def zero_rank(self):
        arcs={q:[] for q in self.pcs}; deg={q:0 for q in self.pcs}; rank={q:0 for q in self.pcs}
        for e in self.edges:
            if e.kind=='repair': arcs[e.src].append(e.dst); deg[e.dst]+=1
        todo=[q for q in self.pcs if deg[q]==0]; seen=0
        while todo:
            q=todo.pop(); seen+=1
            for z in arcs[q]:
                rank[z]=max(rank[z],rank[q]+1); deg[z]-=1
                if deg[z]==0: todo.append(z)
        if seen!=len(self.pcs): raise InvalidModel('zero-base-event repair edges must be acyclic')
        return rank
    @property
    def outgoing(self): return {q:tuple(e for e in self.edges if e.src==q) for q in self.pcs}
    @property
    def inv(self): return dict(self.invariants)
    @property
    def atom_index(self): return {a:i for i,(a,_) in enumerate(self.atoms)}

def parse(raw):
    fields={'name','locations','initial','constants','urgent','invariants','atoms','edges','cap'}
    if type(raw) is not dict or set(raw)!=fields: raise InvalidModel('model fields')
    if type(raw['locations']) is not list or not 1<=len(raw['locations'])<=48: raise InvalidModel('locations')
    pcs=tuple(identifier(q) for q in raw['locations'])
    if len(set(pcs))!=len(pcs): raise InvalidModel('duplicate locations')
    init=raw['initial']
    if type(init) is not dict or set(init)!={'pc','taint','pending'}: raise InvalidModel('initial fields')
    if type(init['taint']) is not bool or type(init['pending']) is not bool: raise InvalidModel('initial Boolean')
    initial=identifier(init['pc'])
    if initial not in pcs: raise InvalidModel('initial location')
    if type(raw['constants']) is not list: raise InvalidModel('constants')
    constants=tuple(integer(x,256) for x in raw['constants'])
    if not constants or constants[0]!=0 or tuple(sorted(set(constants)))!=constants: raise InvalidModel('canonical constants')
    def guard(g):
        if type(g) is not list or len(g)>8: raise InvalidModel('guard array')
        out=[]
        for a in g:
            if type(a) is not list or len(a)!=2 or type(a[0]) is not str or a[0] not in OPS: raise InvalidModel('guard atom')
            c=integer(a[1],256)
            if c not in constants: raise InvalidModel('undeclared guard constant')
            out.append((a[0],c))
        return tuple(out)
    if type(raw['urgent']) is not list: raise InvalidModel('urgent')
    urg=tuple(identifier(q) for q in raw['urgent'])
    if len(set(urg))!=len(urg) or not set(urg)<=set(pcs): raise InvalidModel('urgent locations')
    if type(raw['invariants']) is not dict: raise InvalidModel('invariants')
    inv=tuple(sorted((identifier(q),guard(g)) for q,g in raw['invariants'].items()))
    if len({q for q,_ in inv})!=len(inv) or not {q for q,_ in inv}<=set(pcs): raise InvalidModel('invariant keys')
    if type(raw['atoms']) is not list or len(raw['atoms'])>12: raise InvalidModel('at most twelve repair atoms')
    atoms=[]
    for a in raw['atoms']:
        if type(a) is not dict or set(a)!={'id','cost'}: raise InvalidModel('atom fields')
        atoms.append((identifier(a['id']),integer(a['cost'],256)))
    if len({a for a,_ in atoms})!=len(atoms): raise InvalidModel('duplicate atoms')
    atoms=tuple(atoms); names={a for a,_ in atoms}
    if type(raw['edges']) is not list or not 1<=len(raw['edges'])<=128: raise InvalidModel('edges')
    edges=[]; efields={'id','src','dst','kind','guard','reset','resume','t_clear','p_clear'}
    for e in raw['edges']:
        if type(e) is not dict or set(e)!=efields: raise InvalidModel('edge fields; data-dependent guards and repair time effects unsupported')
        kind=e['kind']
        if type(kind) is not str or kind not in ACTIONS: raise InvalidModel('action not in disjunctive fragment')
        if type(e['reset']) is not bool: raise InvalidModel('reset must be Boolean')
        src=identifier(e['src']); dst=None if e['dst'] is None else identifier(e['dst']); resume=None if e['resume'] is None else identifier(e['resume'])
        if src not in pcs: raise InvalidModel('source')
        if kind=='return':
            if dst is not None or resume is not None: raise InvalidModel('return endpoints')
        elif kind=='interrupt':
            if dst not in pcs or resume not in pcs: raise InvalidModel('interrupt endpoints')
        elif dst not in pcs or resume is not None: raise InvalidModel('ordinary endpoints')
        tc=None if e['t_clear'] is None else identifier(e['t_clear']); pc=None if e['p_clear'] is None else identifier(e['p_clear'])
        if (tc is not None and tc not in names) or (pc is not None and pc not in names): raise InvalidModel('unknown repair atom')
        if kind=='repair' and (e['guard'] or e['reset']): raise InvalidModel('repair steps must be unconditional and clock-transparent')
        edges.append(Edge(identifier(e['id']),src,dst,kind,guard(e['guard']),e['reset'],resume,tc,pc))
    if len({e.id for e in edges})!=len(edges): raise InvalidModel('duplicate transition id')
    if type(raw['cap']) is not list or len(raw['cap'])!=3: raise InvalidModel('cap')
    cap=tuple(integer(v,h) for v,h in zip(raw['cap'],(32,8,8)))
    m=Model(identifier(raw['name']),pcs,initial,init['taint'],init['pending'],constants,frozenset(urg),inv,atoms,tuple(edges),cap)
    m.zero_rank
    if not holds(m,0,m.inv.get(initial,())): raise InvalidModel('initial invariant')
    return m

def regions(m):
    out=[]
    for i,c in enumerate(m.constants):
        out.append((2*c,2*c))
        if i+1<len(m.constants): out.append((2*c,2*m.constants[i+1]))
    out.append((2*m.constants[-1],None))
    return out

def holds(m,r,g):
    lo,hi=regions(m)[r]
    # twice a rational representative; all endpoints are integer comparisons.
    v=lo if hi==lo else lo+1 if hi is None else (lo+hi)/2
    for op,c in g:
        target=2*c
        if not {'<':v<target,'<=':v<=target,'==':v==target,'>=':v>=target,'>':v>target}[op]: return False
    return True

@dataclass(frozen=True)
class _Structure:
    """Invocation-local indices for immutable model structure, never a cache."""
    outgoing:object; inv:object; atom_index:object; representatives:tuple
    def holds(self,r,g):
        v=self.representatives[r]
        for op,c in g:
            target=2*c
            if not {'<':v<target,'<=':v<=target,'==':v==target,'>=':v>=target,'>':v>target}[op]: return False
        return True

def _prepare(m):
    # Parsed models contain only immutable fields. Hand-built models can carry
    # lists or other mutable objects despite frozen dataclass attributes; those
    # retain the original fresh-read path, including reads after callbacks.
    def immutable(x):
        if type(x) in (str,int,bool,type(None)): return True
        if type(x) in (tuple,frozenset): return all(immutable(v) for v in x)
        if type(x) is Edge: return all(immutable(getattr(x,k)) for k in Edge.__dataclass_fields__)
        return False
    if type(m) is not Model or not all(immutable(getattr(m,k)) for k in Model.__dataclass_fields__): return None
    representatives=tuple(lo if hi==lo else lo+1 if hi is None else (lo+hi)/2 for lo,hi in regions(m))
    return _Structure(MappingProxyType(m.outgoing),MappingProxyType(m.inv),MappingProxyType(m.atom_index),representatives)

# State is (event count, delivery count, peak stack depth, location, region, stack).
def initial_state(m): return (0,0,0,m.initial,0,())

def successors(m,s):
    yield from _successors(m,s,None)

def _successors(m,s,structure):
    n,k,h,q,r,stack=s; inv=m.inv if structure is None else structure.inv
    truth=(lambda r,g: holds(m,r,g)) if structure is None else structure.holds
    if q not in m.urgent and r+1<(len(regions(m)) if structure is None else len(structure.representatives)) and truth(r+1,inv.get(q,())):
        yield ('delay',r+1),(n,k,h,q,r+1,stack),None
    for e in (m.outgoing if structure is None else structure.outgoing)[q]:
        if e.kind!='repair' and n>=m.cap[0]: continue
        if not truth(r,e.guard): continue
        nk=k+(e.kind=='interrupt'); ns=stack; nh=h
        if nk>m.cap[1]: continue
        if e.kind=='interrupt':
            if len(stack)>=m.cap[2]: continue
            ns=stack+(e.resume,); dest=e.dst; nh=max(h,len(ns))
        elif e.kind=='return':
            if not stack: continue
            dest=stack[-1]; ns=stack[:-1]
        else: dest=e.dst
        nr=0 if e.reset else r
        if truth(nr,inv.get(dest,())): yield ('edge',e.id),(n+int(e.kind!='repair'),int(nk),nh,dest,nr,ns),e
