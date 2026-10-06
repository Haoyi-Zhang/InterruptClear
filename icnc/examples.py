"""Owned defensive models for falsifying the repair/frontier assertions."""
from .model import parse

def edge(id,src,dst,kind='nop',guard=(),reset=False,resume=None,t_clear=None,p_clear=None):
    return dict(id=id,src=src,dst=dst,kind=kind,guard=[list(a) for a in guard],reset=reset,resume=resume,t_clear=t_clear,p_clear=p_clear)

def model(name,pcs,edges,atoms=(),taint=False,pending=False,cap=(6,2,2),constants=(0,),urgent=None,invariants=None):
    return parse({'name':name,'locations':pcs,'initial':{'pc':pcs[0],'taint':taint,'pending':pending},'constants':list(constants),'urgent':pcs if urgent is None else urgent,'invariants':invariants or {},'atoms':[{'id':a,'cost':c} for a,c in atoms],'edges':edges,'cap':list(cap)})

def fixed():
    out=[]
    # An ordinary clear cuts the initial cause; a pending cause needs its own cut.
    out.append(model('F01-direct-use',['c0','done'],[edge('use','c0','done','use',t_clear='C')],[('C',1)],taint=True,cap=(1,0,0)))
    out.append(model('F02-deferred-cause',['c0','c1','c2','done'],[edge('visible-clean','c0','c1',t_clear='C'),edge('commit','c1','c2','commit',p_clear='P'),edge('use','c2','done','use',t_clear='U')],[('C',1),('P',2),('U',3)],taint=True,pending=True,cap=(3,0,0)))
    # All bad prefixes, including a budget-truncated handler, are observations.
    out.append(model('F03-truncated-handler',['c0','done','h0','h1'],[edge('call','c0','h0','interrupt',resume='done'),edge('inside-use','h0','h1','use',t_clear='C'),edge('return','h1',None,'return')],[('C',1)],taint=True,cap=(2,1,1)))
    out.append(model('F04-returned-handler',['c0','done','h0','h1'],[edge('call','c0','h0','interrupt',resume='done'),edge('inside-use','h0','h1','use',t_clear='C'),edge('return','h1',None,'return')],[('C',1)],taint=True,cap=(3,1,1)))
    # Point/open timing and typed labels are preserved. Repairs do not reset x.
    out.append(model('F05-label-collision',['c0','c1','done','h0'],[edge('delay->(0,1)','c0','h0','interrupt',guard=(('==',1),),resume='c1'),edge('return','h0',None,'return'),edge('use','c1','done','use',t_clear='C')],[('C',1)],taint=True,cap=(3,1,1),constants=(0,1),urgent=['c1','done','h0'],invariants={'c0':[['<=',1]]}))
    out.append(model('F06-open-window',['c0','c1','done'],[edge('window','c0','c1',guard=(('>',0),('<',1))),edge('use','c1','done','use',t_clear='C')],[('C',1)],taint=True,cap=(2,0,0),constants=(0,1),urgent=['c1','done']))
    out.append(model('F07-infeasible-window',['c0','c1','done'],[edge('after','c0','c1',guard=(('>',1),)),edge('use','c1','done','use',guard=(('<=',1),),t_clear='C')],[('C',1)],taint=True,cap=(2,0,0),constants=(0,1),urgent=['c1','done']))
    # Two resources must be retained jointly. Different costs trade off.
    out.append(model('F08-resource-tradeoff',['c0','c1','c2','done','h0'],[edge('call','c0','h0','interrupt',resume='done'),edge('fast-use','h0','h0','use',t_clear='A'),edge('return','h0',None,'return'),edge('long1','c0','c1'),edge('long2','c1','c2'),edge('slow-use','c2','done','use',t_clear='B')],[('A',2),('B',1)],taint=True,cap=(3,1,1)))
    out.append(model('F09-nested-cause',['c0','done','h0','h1','n0','n1'],[edge('call','c0','h0','interrupt',resume='done'),edge('clean','h0','h1','neutralize'),edge('nested','h1','n0','interrupt',resume='h1'),edge('arm','n0','n1','arm'),edge('nested-return','n1',None,'return',t_clear='N'),edge('use','h1','h1','use',t_clear='U'),edge('return','h1',None,'return')],[('N',1),('U',2)],taint=True,cap=(6,2,2)))
    out.append(model('F10-unrepairable-source',['c0','c1','done'],[edge('ineffective-clear','c0','c1','arm',t_clear='C'),edge('use','c1','done','use')],[('C',1)],cap=(2,0,0)))
    out.append(model('F11-alternative-cuts',['c0','a','b','done'],[edge('a1','c0','a',t_clear='A'),edge('au','a','done','use',t_clear='B'),edge('b1','c0','b',t_clear='B'),edge('bu','b','done','use',t_clear='C')],[('A',1),('B',3),('C',1)],taint=True,cap=(2,0,0)))
    # Distinct histories at join: both dirty facts are possible but not jointly.
    out.append(model('F12-disjunctive-join',['c0','a','b','j','k','done'],[edge('arm','c0','a','arm'),edge('schedule','c0','b','schedule'),edge('aj','a','j',t_clear='A'),edge('bj','b','j',p_clear='B'),edge('commit','j','k','commit'),edge('use','k','done','use')],[('A',1),('B',1)],cap=(4,0,0)))
    return out

def threshold(m,k):
    """Select exactly k sites out of m; all binomial(m,k) obstructions survive."""
    if not 1<=k<=m<=8: raise ValueError('threshold domain')
    coords=[(i,j) for i in range(m+1) for j in range(k+1) if j<=i and k-j<=m-i]
    pcs=[f'q{i}_{j}' for i,j in coords]+['done']; edges=[]
    for i,j in coords:
        if i==m: continue
        if (i+1,j) in coords: edges.append(edge(f'skip{i}_{j}',f'q{i}_{j}',f'q{i+1}_{j}'))
        if (i+1,j+1) in coords: edges.append(edge(f'pick{i}_{j}',f'q{i}_{j}',f'q{i+1}_{j+1}',t_clear=f'A{i}'))
    edges.append(edge('use',f'q{m}_{k}','done','use'))
    return model(f'T{m}-{k}',pcs,edges,[(f'A{i}',1) for i in range(m)],taint=True,cap=(m+1,0,0))

def grammar():
    """A declared 64-model finite grammar, not a workload sample."""
    actions=('nop','arm','schedule','commit')
    for idx in range(64):
        a=actions[idx&3]; b=actions[(idx>>2)&3]; taint=bool(idx&16); pending=bool(idx&32)
        yield model(f'G{idx:02d}',['c0','c1','c2','done'],[edge('one','c0','c1',a,t_clear='A'),edge('two','c1','c2',b,p_clear='B'),edge('use','c2','done','use',t_clear='A')],[('A',1),('B',2)],taint=taint,pending=pending,cap=(3,0,0))

def lowering_cases():
    # Each case is a base model and an explicit interruption-exposed repair word.
    def mk(name,action,taint,pending,word,return_clear=False):
        # return_clear models a separate primitive after the handler action by
        # another explicit word, not an atomic-before-use assumption.
        b=model(name,['c0','c1','done','h0','h1'],[
            edge('start','c0','c1'),edge('irq','c1','h0','interrupt',resume='c1'),
            edge('use','c1','done','use'),edge('handler','h0','h1',action),edge('ret','h1',None,'return')],
            [(a,c) for a,c in [('P',1),('C',1),('R',3)] if a in {x for x,bit in word} or (a=='R' and return_clear)],taint=taint,pending=pending,cap=(5,1,1))
        words={'c1':word}
        if return_clear: words['h1']=[('R','t')]
        return b,words
    return [mk('L01-drain-clean','commit',True,True,[('P','p'),('C','t')]),
            mk('L02-clean-drain','commit',True,True,[('C','t'),('P','p')]),
            mk('L03-clean-repoison','arm',True,False,[('C','t')]),
            mk('L04-return-repair','arm',True,False,[('C','t')],True)]


def ordering_words():
    """All 31 active-word shapes of length at most four over clear P/C.

    Atom selection removes the corresponding clears semantically, not the
    interruption-exposed slots.  No initial cause is regenerated by the handler.
    """
    from itertools import product
    base=model('order-law',['c0','c1','done','h0','h1'],[
        edge('start','c0','c1'),edge('irq','c1','h0','interrupt',resume='c1'),
        edge('use','c1','done','use'),edge('handler','h0','h1','commit'),edge('ret','h1',None,'return')],
        [('P',1),('C',1)],taint=True,pending=True,cap=(5,1,1))
    for length in range(5):
        for letters in product('PC',repeat=length):
            word=[(a,'p' if a=='P' else 't') for a in letters]
            yield base,{'c1':word},''.join(letters)
