"""Reproduce the declared, benign, bounded model study from this directory."""
from __future__ import annotations
import argparse,csv,json,resource,time,copy
from pathlib import Path
import solver,verify,oracle

HERE=Path(__file__).resolve().parent

def run(out:Path):
    resource.setrlimit(resource.RLIMIT_AS,(2500*1024*1024,2500*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(170,180))
    start=time.process_time();wall=time.monotonic();out.mkdir(parents=True,exist_ok=True);(out/'certificates').mkdir(exist_ok=True)
    p=json.loads((HERE/'protocol.json').read_text());index=json.loads((HERE/'models/index.json').read_text())
    models={r['id']:solver.load(HERE/'models'/f"{r['id']}.json") for r in index}
    rows=[];oracle_rows=[];sensitivity=[];omissions=[];work=0;states_total=0
    def charge(n):
        nonlocal work
        work+=n
        if work+verify.WORK_TOTAL>p['work_cap']:raise RuntimeError('command work cap exceeded')
    for r in index:
        m=models[r['id']];s=solver.explore(m,p['main_events'],p['main_interrupts']);charge(s['obligations']);states_total+=s['states']
        if states_total>p['state_cap']:raise RuntimeError('command state cap exceeded')
        if s['safe']!=r['expected']:raise AssertionError('unexpected verdict '+r['id'])
        certfile=out/'certificates'/f"{r['id']}.json";certfile.write_text(json.dumps(s['certificate'],separators=(',',':'))+'\n')
        v=verify.check(verify.read_json(HERE/'models'/f"{r['id']}.json",262144),verify.read_json(certfile,16777216),p['main_events'],p['main_interrupts'])
        if (v['verdict']=='SAFE')!=s['safe']:raise AssertionError('verdict disagreement')
        a=solver.explore(m,p['oracle_events'],p['oracle_interrupts']);charge(a['obligations'])
        b=oracle.explore(m,p['oracle_events'],p['oracle_interrupts']);charge(b['constraint_systems'])
        if a['reachable']!=b['reachable'] or a['safe']!=b['safe']:raise AssertionError('oracle discrepancy '+r['id'])
        oracle_rows.append({'id':r['id'],'states':len(b['reachable']),'feasible_prefixes':b['feasible_prefixes'],'constraint_systems':b['constraint_systems'],'match':True})
        integer=solver.explore(m,p['main_events'],p['main_interrupts'],integer_only=True);charge(integer['obligations'])
        rows.append({'id':r['id'],'locations':len(m['nodes']),'edges':len(m['edges']),'max_constant':solver.maximum(m),'safe':s['safe'],'states':s['states'],'obligations':s['obligations'],'verifier_obligations':v['obligations'],'integer_safe':integer['safe'],'certificate_bytes':certfile.stat().st_size,'diagnostic_length':0 if s['safe'] else len(s['certificate']['steps'])})
    for id in p['sensitivity_models']:
        for n in p['sensitivity_events']:
            for k in p['sensitivity_interrupts']:
                s=solver.explore(models[id],n,k);charge(s['obligations'])
                sensitivity.append({'id':id,'events':n,'interrupts':k,'safe':s['safe'],'states':s['states'],'obligations':s['obligations']})
    for id,edge in p['omissions']:
        m=copy.deepcopy(models[id])
        if id=='C01':
            # Preserve the transition and timing, but erase the use observation.
            next(e for e in m['edges'] if e['id']==edge)['kind']='step'
        else:m['edges']=[e for e in m['edges'] if e['id']!=edge]
        s=solver.explore(m,32,8);charge(s['obligations']);v=verify.check(m,s['certificate'],32,8)
        if not s['safe']:raise AssertionError('omission control did not discriminate')
        omissions.append({'id':id,'omitted_obligation':edge,'complete_model_safe':False,'modified_model_safe':s['safe'],'modified_verifier':v['verdict']})
    for name,data in [('models',rows),('oracle',oracle_rows),('sensitivity',sensitivity),('omissions',omissions)]:
        with (out/f'{name}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    deterministic={'models':rows,'oracle':oracle_rows,'sensitivity':sensitivity,'omissions':omissions,
      'total_full_states':sum(r['states'] for r in rows),'total_full_obligations':sum(r['obligations'] for r in rows),'total_oracle_systems':sum(r['constraint_systems'] for r in oracle_rows),
      'total_work':work+verify.WORK_TOTAL,'verifier_work':verify.WORK_TOTAL,'workers':1,'safe_models':sum(r['safe'] for r in rows),'unsafe_models':sum(not r['safe'] for r in rows)}
    (out/'reference.json').write_text(json.dumps(deterministic,indent=2)+'\n')
    (out/'measurements.json').write_text(json.dumps({'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1},indent=2)+'\n')
    print(json.dumps({k:v for k,v in deterministic.items() if not isinstance(v,list)},indent=2));print((out/'measurements.json').read_text())
    return deterministic

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=HERE/'results/reproduced');p.add_argument('--compare',type=Path)
    a=p.parse_args();result=run(a.output)
    if a.compare:
        ref=json.loads(a.compare.read_text())
        if ref!=result:raise SystemExit('deterministic result mismatch')
        print('All deterministic results match the retained reference.')
