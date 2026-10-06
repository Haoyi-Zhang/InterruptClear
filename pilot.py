#!/usr/bin/env python3
"""Discriminating pre-lock pilot; writes measured evidence, not a PASS banner."""
import argparse,itertools,json,time
from icnc.runtime_limits import configure_limits,check_cpu_limit,peak_rss_kib
from pathlib import Path
from icnc.examples import fixed,threshold,model,edge
from icnc.frontier import Meter,build,unsafe,synthesize
from icnc.direct import explore
from icnc.lowering import expand,projection_obligations
ROOT=Path(__file__).resolve().parent

def run():
    start=time.process_time(); meter=Meter(limit=20000); rows=[]
    for m in fixed()+[threshold(4,2)]:
        a=build(m,meter); q=0
        for x in range(1<<len(m.atoms)):
            direct=explore(m,x,meter)
            for cap in itertools.product(*(range(v+1) for v in m.cap)):
                actual=any(all(c<=b for c,b in zip(cost,cap)) for cost in direct['bad_costs'])
                assert actual==unsafe(a['frontier'],x,cap),(m.name,x,cap)
                q+=1
        rows.append({'model':m.name,'frontier':[list(z) for z in a['frontier']],'query_comparisons':q,'optimum':synthesize(m,a['frontier'],m.cap)})
    base=model('pending-order',['c0','c1','done','h0','h1'],[edge('start','c0','c1'),edge('irq','c1','h0','interrupt',resume='c1'),edge('use','c1','done','use'),edge('commit','h0','h1','commit'),edge('ret','h1',None,'return')],[('P',1),('C',1)],taint=True,pending=True,cap=(5,1,1))
    order=[]
    for word in [[('P','p'),('C','t')],[('C','t'),('P','p')]]:
        lowered,projection,origins=expand(base,{'c1':word}); projection_obligations(base,lowered,projection,origins,{'c1':word})
        a=build(lowered,meter); d=explore(lowered,3,meter)
        assert d['safe']==(word[0][0]=='P')
        order.append({'word':word,'frontier':[list(z) for z in a['frontier']],'all_atoms_safe':d['safe']})
    check_cpu_limit()
    return {'fixed_and_threshold':rows,'order_negative_control':order,'measured':{'cpu_seconds':time.process_time()-start,'peak_rss_kib':peak_rss_kib(),'workers':1,'charged_operations':meter.counts},'scope':'owned models; no hardware or empirical deployment evidence'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--portable',action='store_true');ap.add_argument('--output',type=Path,default=ROOT/'results'/'pilot.json');args=ap.parse_args()
    limits=configure_limits(portable=args.portable)
    result=run();result['measured']['runtime_limits']=limits
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['order_negative_control'],indent=2)); print(result['measured'])
