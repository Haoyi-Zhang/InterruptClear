"""Small high-level repair-word interpreter, separate from phase-graph lowering.

Program counters are (base location, progress through the repair word). This
runs explicit Booleans under each plan and does not call the lowering routine.
For differential timing evidence use oracle.py (this interpreter intentionally
uses the same validated model's region truth function).
"""
from collections import deque
from .model import holds,regions

def explore(base,words,plan,charge=None):
    # (n,k,h,q,phase,r,stack,t,p), stack consists of high-level (q,phase) pairs.
    root=(0,0,0,base.initial,0,0,(),base.taint,base.pending)
    seen={root};todo=deque([root]);bad=set();ai=base.atom_index
    while todo:
        s=todo.popleft();n,k,h,q,j,r,stack,t,p=s
        if q not in base.urgent and r+1<len(regions(base)) and holds(base,r+1,base.inv.get(q,())):
            z=(n,k,h,q,j,r+1,stack,t,p)
            if charge:charge('word_delay')
            if z not in seen:seen.add(z);todo.append(z)
        word=words.get(q,())
        if j<len(word):
            a,bit=word[j];nt,np=t,p
            if plan&(1<<ai[a]):
                if bit=='t':nt=False
                else:np=False
            z=(n,k,h,q,j+1,r,stack,nt,np)
            if charge:charge('word_repair')
            if z not in seen:seen.add(z);todo.append(z)
        if n==base.cap[0]:continue
        for e in base.outgoing[q]:
            if j<len(word) and e.kind!='interrupt':continue
            if not holds(base,r,e.guard):continue
            nk=k+int(e.kind=='interrupt');nh=h;st=stack
            if nk>base.cap[1]:continue
            if e.kind=='interrupt':
                if len(stack)>=base.cap[2]:continue
                st=stack+((e.resume,j if e.resume==q else 0),);nh=max(h,len(st));dest=e.dst;phase=0
            elif e.kind=='return':
                if not stack:continue
                dest,phase=stack[-1];st=stack[:-1]
            else:dest=e.dst;phase=0
            nr=0 if e.reset else r
            if not holds(base,nr,base.inv.get(dest,())):continue
            if charge:charge('word_base_edge')
            nt,np=t,p
            if e.kind=='use' and nt:bad.add((n+1,nk,nh))
            if e.kind=='arm':nt=True
            if e.kind=='neutralize':nt=False
            if e.kind=='schedule':np=True
            if e.kind=='clear_pending':np=False
            if e.kind=='commit':nt=nt or np;np=False
            z=(n+1,nk,nh,dest,phase,nr,st,nt,np)
            if z not in seen:seen.add(z);todo.append(z)
    return {'states':seen,'bad_costs':bad,'safe':not bad}
