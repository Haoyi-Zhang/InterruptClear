"""Exact small oracle: path enumeration plus strict difference constraints.

No region transition relation, generator code, or verifier code is imported.
Input is the same declarative graph. A distance bound is (integer, strict).
"""
from __future__ import annotations

def tighter(a,b):
    if b is None:return True
    return a[0]<b[0] or (a[0]==b[0] and a[1] and not b[1])

def feasible(size,constraints):
    d=[[None]*size for _ in range(size)]
    for i in range(size):d[i][i]=(0,False)
    # x_i - x_j <= c, or < c when strict.
    for i,j,c,s in constraints:
        val=(c,s)
        if tighter(val,d[j][i]):d[j][i]=val
    for k in range(size):
        for i in range(size):
            if d[i][k] is None:continue
            for j in range(size):
                if d[k][j] is None:continue
                a,b=d[i][k],d[k][j];v=(a[0]+b[0],a[1] or b[1])
                if tighter(v,d[i][j]):d[i][j]=v
    return not any(d[i][i][0]<0 or (d[i][i][0]==0 and d[i][i][1]) for i in range(size))

def atoms(guard,now,reset_at):
    c=[]
    for op,v in guard:
        if op in ('<','<=','=='):c.append((now,reset_at,v,op=='<'))
        if op in ('>','>=','=='):c.append((reset_at,now,-v,op=='>'))
    return c

def explore(m,events=6,interrupts=2,limit=200000):
    ns={s['id']:s for s in m['nodes']};adj={q:[] for q in ns}
    for t in m['edges']:adj[t['src']].append(t)
    M=max([v for t in m['edges'] for _,v in t['guard']]+[0]);states={(0,0,m['initial'],0)}
    feasible_prefixes=1;tests=0;bad=False
    # Path constraints keep actual event-time variables t_0,...,t_n.
    def visit(q,n,k,reset_at,C):
        nonlocal tests,feasible_prefixes,bad
        if n==events:return
        for t in adj[q]:
            nk=k+int(t['kind']=='interrupt')
            if nk>interrupts:continue
            now=n+1;D=C+[(n,now,0,False)]+atoms(t['guard'],now,reset_at)
            tests+=1
            if tests>limit:raise RuntimeError('oracle constraint-system cap')
            if not feasible(now+1,D):continue
            feasible_prefixes+=1
            if t['kind']=='use' and not ns[q]['clean']:bad=True
            nr=now if t['reset'] else reset_at
            for r in range(2*M+2):
                if r==2*M+1:post=[('>',M)]
                elif r%2==0:post=[('==',r//2)]
                else:post=[('>',r//2),('<',r//2+1)]
                tests+=1
                if tests>limit:raise RuntimeError('oracle constraint-system cap')
                if feasible(now+1,D+atoms(post,now,nr)):states.add((now,nk,t['dst'],r))
            visit(t['dst'],now,nk,nr,D)
    visit(m['initial'],0,0,0,[])
    return {'safe':not bad,'reachable':states,'constraint_systems':tests,'feasible_prefixes':feasible_prefixes}
