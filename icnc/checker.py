"""Separate certificate replay. No imports from the producer or region explorer.

A certificate is a topologically ordered, rooted, successor-closed skeleton
with exact two-fact symbolic annotations and the final minimal obstruction set.
The trusted model is supplied separately; its byte contents cannot be replaced
by the model embedded in the certificate. This is separately coded checking,
not independent authorship or a proof-assistant verified implementation.
"""
from __future__ import annotations
import json,unicodedata
from pathlib import Path

class Rejected(ValueError): pass

def require(c,message):
    if not c: raise Rejected(message)

def _int(x,lo,hi):
    require(type(x) is int and lo<=x<=hi,'integer type/range'); return x

def _id(x):
    require(type(x) is str and 0<len(x)<=96,'identifier')
    normalized=unicodedata.normalize('NFC',x)
    require(0<len(normalized)<=96,'normalized identifier length')
    return normalized

def _unique(items):
    out={}
    for k,v in items:
        k=unicodedata.normalize('NFC',k);require(k not in out,'duplicate normalized key');out[k]=v
    return out

def read(path,limit=16*1024*1024):
    raw=Path(path).read_bytes(); require(len(raw)<=limit,'byte cap')
    try: return json.loads(raw,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(Rejected('nonfinite JSON')))
    except (UnicodeError,json.JSONDecodeError,RecursionError) as e: raise Rejected('invalid JSON') from e

def _model(raw):
    require(type(raw) is dict and set(raw)=={'name','locations','initial','constants','urgent','invariants','atoms','edges','cap'},'model fields')
    name=_id(raw['name']); require(type(raw['locations']) is list and 1<=len(raw['locations'])<=48,'locations')
    pcs=tuple(_id(q) for q in raw['locations']); require(len(set(pcs))==len(pcs),'duplicate locations')
    initial=raw['initial'];require(type(initial) is dict and set(initial)=={'pc','taint','pending'},'initial fields')
    q0=_id(initial['pc']);require(q0 in pcs and type(initial['taint']) is bool and type(initial['pending']) is bool,'initial values')
    require(type(raw['constants']) is list,'constants'); const=tuple(_int(x,0,256) for x in raw['constants'])
    require(bool(const) and const[0]==0 and tuple(sorted(set(const)))==const,'constant order')
    def guard(g):
        require(type(g) is list and len(g)<=8,'guard')
        for a in g:
            require(type(a) is list and len(a)==2 and type(a[0]) is str and a[0] in ('<','<=','==','>=','>'),'guard operator')
            _int(a[1],0,256);require(a[1] in const,'undeclared constant')
        return tuple(tuple(a) for a in g)
    require(type(raw['urgent']) is list,'urgent'); urgent=tuple(_id(q) for q in raw['urgent'])
    require(len(set(urgent))==len(urgent) and set(urgent)<=set(pcs),'urgent locations')
    require(type(raw['invariants']) is dict,'invariants');inv={}
    for q,g in raw['invariants'].items():
        q=_id(q); require(q in pcs and q not in inv,'invariant location'); inv[q]=guard(g)
    require(type(raw['atoms']) is list and len(raw['atoms'])<=12,'atoms');atoms=[]
    for a in raw['atoms']:
        require(type(a) is dict and set(a)=={'id','cost'},'atom fields');atoms.append((_id(a['id']),_int(a['cost'],0,256)))
    names=[a for a,c in atoms];require(len(set(names))==len(names),'duplicate atoms')
    require(type(raw['edges']) is list and 1<=len(raw['edges'])<=128,'edges');edges={};out={q:[] for q in pcs}
    zero={q:[] for q in pcs};degree={q:0 for q in pcs}
    for a in raw['edges']:
        require(type(a) is dict and set(a)=={'id','src','dst','kind','guard','reset','resume','t_clear','p_clear'},'edge fields')
        kind=a['kind'];require(type(kind) is str and kind in ('nop','arm','neutralize','schedule','clear_pending','commit','use','interrupt','return','repair'),'action')
        eid=_id(a['id']);require(eid not in edges,'duplicate edge')
        src=_id(a['src']); dst=None if a['dst'] is None else _id(a['dst']); ret=None if a['resume'] is None else _id(a['resume'])
        require(src in pcs,'edge source');require(type(a['reset']) is bool,'reset Boolean')
        if kind=='return': require(dst is None and ret is None,'return shape')
        elif kind=='interrupt': require(dst in pcs and ret in pcs,'interrupt shape')
        else: require(dst in pcs and ret is None,'ordinary shape')
        tc=None if a['t_clear'] is None else _id(a['t_clear']);pc=None if a['p_clear'] is None else _id(a['p_clear'])
        require(tc is None or tc in names,'taint repair atom');require(pc is None or pc in names,'pending repair atom')
        g=guard(a['guard'])
        if kind=='repair':
            require(not g and not a['reset'],'repair clock transparency');zero[src].append(dst);degree[dst]+=1
        edges[eid]=(eid,src,dst,kind,g,a['reset'],ret,None if tc is None else names.index(tc),None if pc is None else names.index(pc))
        out[src].append(edges[eid])
    queue=[q for q in pcs if degree[q]==0]; visited=0
    while queue:
        q=queue.pop();visited+=1
        for d in zero[q]:
            degree[d]-=1
            if degree[d]==0:queue.append(d)
    require(visited==len(pcs),'repair cycle')
    require(type(raw['cap']) is list and len(raw['cap'])==3,'cap')
    cap=tuple(_int(v,0,h) for v,h in zip(raw['cap'],(32,8,8)))
    # Use exact rational values scaled by two; all chosen representatives have
    # half-integer or integer coordinates.
    reps=[]
    for i,c in enumerate(const):
        reps.append(2*c)
        if i+1<len(const):reps.append(c+const[i+1])
    reps.append(2*const[-1]+1)
    normalized={'name':name,'locations':list(pcs),'initial':{'pc':q0,'taint':initial['taint'],'pending':initial['pending']},'constants':list(const),'urgent':sorted(urgent),'invariants':{q:[list(x) for x in g] for q,g in sorted(inv.items())},'atoms':[{'id':a,'cost':c} for a,c in atoms],'edges':[], 'cap':list(cap)}
    for e in edges.values():
        eid,src,dst,kind,g,r,ret,tc,pc=e
        normalized['edges'].append({'id':eid,'src':src,'dst':dst,'kind':kind,'guard':[list(a) for a in g],'reset':r,'resume':ret,'t_clear':None if tc is None else names[tc],'p_clear':None if pc is None else names[pc]})
    return {'raw':normalized,'pcs':pcs,'q0':q0,'t0':initial['taint'],'p0':initial['pending'],'urgent':set(urgent),'inv':inv,'edges':edges,'out':out,'reps':reps,'cap':cap,'atoms':atoms}

def _truth(m,r,g):
    value=m['reps'][r]
    for op,c in g:
        b=2*c
        if op=='<' and value>=b:return False
        if op=='<=' and value>b:return False
        if op=='==' and value!=b:return False
        if op=='>=' and value<b:return False
        if op=='>' and value<=b:return False
    return True

def _arcs(m,s):
    n,k,h,q,r,stack=s;cap=m['cap']
    if q not in m['urgent'] and r+1<len(m['reps']) and _truth(m,r+1,m['inv'].get(q,())):
        yield ('delay',r+1),(n,k,h,q,r+1,stack),None
    for e in m['out'][q]:
        eid,src,dst,kind,g,reset,ret,tc,pc=e
        if n>=cap[0] and kind!='repair':continue
        if not _truth(m,r,g):continue
        nk=k+(kind=='interrupt');st=stack;nh=h
        if nk>cap[1]:continue
        if kind=='interrupt':
            if len(st)>=cap[2]:continue
            st=st+(ret,);nh=max(h,len(st));loc=dst
        elif kind=='return':
            if not st:continue
            loc=st[-1];st=st[:-1]
        else:loc=dst
        region=0 if reset else r
        if _truth(m,region,m['inv'].get(loc,())):
            yield ('edge',eid),(n+(kind!='repair'),int(nk),nh,loc,region,st),e

def _min(values):
    unique=set(values)
    return tuple(sorted(v for v in unique if not any(u!=v and (u&v)==u for u in unique)))

def _ann(m,e,t,p):
    if e is None:return t,p,()
    eid,src,dst,kind,g,reset,ret,tc,pc=e
    if tc is not None:t=_min(tuple(v|(1<<tc) for v in t))
    if pc is not None:p=_min(tuple(v|(1<<pc) for v in p))
    bad=t if kind=='use' else ()
    if kind=='arm':t=(0,)
    if kind=='neutralize':t=()
    if kind=='schedule':p=(0,)
    if kind=='clear_pending':p=()
    if kind=='commit':t=_min(t+p);p=()
    return t,p,bad

def _front(values):
    unique=set(values)
    def dom(a,b):return a[0]&b[0]==a[0] and all(x<=y for x,y in zip(a[1:],b[1:]))
    return tuple(sorted(v for v in unique if not any(u!=v and dom(u,v) for u in unique)))

def check(trusted,certificate,charge=None):
    m=_model(trusted)
    def spend(kind,n=1):
        if charge:charge(kind,n)
    require(type(certificate) is dict and set(certificate)=={'schema','model','nodes','frontier'},'certificate fields')
    require(certificate['schema']=='neutralization-frontier','schema')
    # Independently normalize the embedded model and compare with the trusted
    # one; a certificate cannot remove observations by supplying a new model.
    inner=_model(certificate['model'])
    require(inner['raw']==m['raw'],'model mismatch')
    entries=certificate['nodes'];require(type(entries) is list and 1<=len(entries)<=250000,'nodes')
    root=(0,0,0,m['q0'],0,()); require(_truth(m,0,m['inv'].get(m['q0'],())),'initial invariant')
    states=[];indices={};ann=[]
    maxmask=(1<<len(m['atoms']))-1
    for i,entry in enumerate(entries):
        require(type(entry) is dict and set(entry)=={'state','parent','t','p'},'node fields')
        row=entry['state'];require(type(row) is list and len(row)==6,'state row')
        n=_int(row[0],0,m['cap'][0]);k=_int(row[1],0,m['cap'][1]);h=_int(row[2],0,m['cap'][2]);q=_id(row[3]);r=_int(row[4],0,len(m['reps'])-1)
        require(q in m['pcs'] and k<=n and h<=k,'state coordinates')
        require(type(row[5]) is list and len(row[5])<=h,'stack');stack=tuple(_id(q) for q in row[5]); require(set(stack)<=set(m['pcs']),'stack locations')
        s=(n,k,h,q,r,stack);require(s not in indices,'duplicate state');require(_truth(m,r,m['inv'].get(q,())),'state invariant')
        states.append(s);indices[s]=i
        parsed=[]
        for field in ('t','p'):
            xs=entry[field];require(type(xs) is list,'annotation list')
            for x in xs:_int(x,0,maxmask)
            require(tuple(xs)==_min(xs),'annotation not canonical'); parsed.append(tuple(xs));spend('checker_terms',len(xs))
        ann.append(tuple(parsed))
        par=entry['parent']
        if i==0:require(s==root and par is None,'root')
        else:
            require(type(par) is list and len(par)==2,'parent');j=_int(par[0],0,i-1)
            label=par[1];require(type(label) is list and len(label)==2 and label[0] in ('delay','edge'),'parent label')
            if label[0]=='delay':_int(label[1],0,len(m['reps'])-1)
            else:_id(label[1])
            require(any(l==tuple(label) and z==s for l,z,e in _arcs(m,states[j])),'parent not enabled')
            spend('checker_parent')
    values=[((),()) for _ in states];values[0]=((0,) if m['t0'] else (), (0,) if m['p0'] else ())
    obligations=[]
    for i,s in enumerate(states):
        require(values[i]==ann[i],'annotation recurrence mismatch')
        for label,z,e in _arcs(m,s):
            spend('checker_arcs');require(z in indices,'successor omitted');j=indices[z];require(j>i,'not topological')
            t,p,bad=_ann(m,e,*values[i]);ot,op=values[j];values[j]=(_min(ot+t),_min(op+p))
            for mask in bad:obligations.append((mask,*z[:3]));spend('checker_bad')
    raw=certificate['frontier'];require(type(raw) is list,'frontier')
    for row in raw:
        require(type(row) is list and len(row)==4,'frontier row');_int(row[0],0,maxmask)
        for x,hi in zip(row[1:],m['cap']):_int(x,0,hi)
    expected=_front(obligations)
    require(tuple(tuple(v) for v in raw)==expected,'frontier equality')
    return {'checked_nodes':len(states),'checked_frontier_records':len(expected),'annotation_equality':True,'reachable_and_closed':True}
