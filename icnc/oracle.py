"""Exact finite control-path oracle using strict difference constraints.

This module imports neither the frontier, region semantics, nor checker. It
expects a validated raw model. It carries explicit Boolean values, a concrete
return stack and absolute event-time variables. Pure delays are collected by
querying each possible region after each feasible discrete prefix.
"""
from __future__ import annotations

def feasible(size,constraints):
    # Constraints (i,j,c,strict) mean t_i-t_j <= c or < c.
    d=[[None]*size for _ in range(size)]
    for i in range(size): d[i][i]=(0,False)
    def tighter(a,b):return b is None or a[0]<b[0] or (a[0]==b[0] and a[1] and not b[1])
    for i,j,c,st in constraints:
        v=(c,st)
        if tighter(v,d[j][i]):d[j][i]=v
    for k in range(size):
        for i in range(size):
            if d[i][k] is None:continue
            for j in range(size):
                if d[k][j] is None:continue
                a,b=d[i][k],d[k][j];v=(a[0]+b[0],a[1] or b[1])
                if tighter(v,d[i][j]):d[i][j]=v
    return not any(d[i][i][0]<0 or d[i][i]==(0,True) for i in range(size))

def inequalities(atoms,now,reset):
    out=[]
    for op,c in atoms:
        if op in ('<','<=','=='):out.append((now,reset,c,op=='<'))
        if op in ('>','>=','=='):out.append((reset,now,-c,op=='>'))
    return out

def explore(raw,plan,charge=None,limit=30000):
    pcs=raw['locations'];constants=raw['constants'];inv=raw['invariants'];urgent=set(raw['urgent']);cap=raw['cap']
    outgoing={q:[] for q in pcs}
    for e in raw['edges']:outgoing[e['src']].append(e)
    ai={a['id']:i for i,a in enumerate(raw['atoms'])}; region_guards=[]
    for i,c in enumerate(constants):
        region_guards.append([('==',c)])
        if i+1<len(constants):region_guards.append([('>',c),('<',constants[i+1])])
    region_guards.append([('>',constants[-1])])
    states=set();bad=set();systems=0;paths=0
    def check(size,cs):
        nonlocal systems
        systems+=1
        if systems>limit:raise RuntimeError('oracle bound exceeded; no verdict')
        if charge:charge('oracle_constraints')
        return feasible(size,cs)
    def visit(q,stack,n,k,h,t,p,last,reset,cs):
        nonlocal paths
        paths+=1
        # Include arbitrary time elapse after this prefix, not only clocks at a
        # subsequent event; this also covers terminal and event-limit states.
        now=last+1
        wait=cs+[(last,now,0,False)]+inequalities(inv.get(q,()),now,reset)
        if q in urgent:wait.append((now,last,0,False))
        for r,g in enumerate(region_guards):
            if check(now+1,wait+inequalities(g,now,reset)):
                states.add((n,k,h,q,r,stack,t,p))
        for e in outgoing[q]:
            kind=e['kind']
            if n>=cap[0] and kind!='repair':continue
            nk=k+int(kind=='interrupt');nh=h;st=stack
            if nk>cap[1]:continue
            if kind=='interrupt':
                if len(stack)>=cap[2]:continue
                st=stack+(e['resume'],);nh=max(h,len(st));dest=e['dst']
            elif kind=='return':
                if not stack:continue
                dest=stack[-1];st=stack[:-1]
            else:dest=e['dst']
            newreset=now if e['reset'] else reset
            ext=wait+inequalities(e['guard'],now,reset)+inequalities(inv.get(dest,()),now,newreset)
            if not check(now+1,ext):continue
            nt,np=t,p
            if e['t_clear'] is not None and plan&(1<<ai[e['t_clear']]):nt=False
            if e['p_clear'] is not None and plan&(1<<ai[e['p_clear']]):np=False
            nn=n+int(kind!='repair')
            if kind=='use' and nt:bad.add((nn,nk,nh))
            if kind=='arm':nt=True
            if kind=='neutralize':nt=False
            if kind=='schedule':np=True
            if kind=='clear_pending':np=False
            if kind=='commit':nt=nt or np;np=False
            visit(dest,st,nn,nk,nh,nt,np,now,newreset,ext)
    i=raw['initial'];visit(i['pc'],(),0,0,0,i['taint'],i['pending'],0,0,[])
    return {'safe':not bad,'bad_costs':bad,'states':states,'constraint_systems':systems,'control_prefixes':paths}
