#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import Counter
from copy import deepcopy
import hashlib, json, os, random, statistics, sys, time
from icnc.generators import separation_models, generated_model, random_model, ood_model, rename_model, permute_model, unreachable_extension
from icnc.model import save_model
from icnc.semantics import explore, initial_state, safety_verdict
from icnc.contract import compare_monolithic_and_contract, episode_outcomes
from icnc.certificate import generate_certificate, verify_certificate
from icnc.oracle import concrete_verdict

ROOT=Path(__file__).resolve().parent
RES=ROOT/'results'; CERT=RES/'certificates'; RES.mkdir(exist_ok=True); CERT.mkdir(exist_ok=True)

def initial_summary(m):
    s=initial_state(m); call=next(t for t in m.outgoing(s.pc) if t.event=='interrupt')
    return episode_outcomes(m,s,call)

def mutate(cert, kind):
    c=deepcopy(cert)
    if kind==0:c['model_sha256']='0'*64
    elif kind==1:c['model_name']+='-forged'
    elif kind==2:c['verdict']='unsafe' if c['verdict']=='safe' else 'safe'
    elif kind==3:c['schema']='icnc-certificate-v0'
    elif kind==4:c['monolithic']['states']=c['monolithic']['states'][1:]
    elif kind==5:c['monolithic']['states'].append(['fake',[],0,False,False,False,0,0])
    elif kind==6:c['monolithic']['edges']=c['monolithic']['edges'][1:]
    elif kind==7:
        if c['monolithic']['edges']:c['monolithic']['edges'][0][1]+='-forged'
        else:c['monolithic']['edges'].append([c['monolithic']['states'][0],'forged',c['monolithic']['states'][0]])
    elif kind==8:c['monolithic']['bad_trace']=[] if c['monolithic']['bad_trace'] else [['forged',c['monolithic']['states'][0]]]
    elif kind==9:c['contract']['states']=c['contract']['states'][1:]
    elif kind==10:c['contract']['states'].append(['fake',[],0,False,False,False,0,0])
    elif kind==11:c['contract']['summaries']=c['contract']['summaries'][1:]
    elif kind==12:
        if c['contract']['summaries'] and c['contract']['summaries'][0]['outcomes']:
            c['contract']['summaries'][0]['outcomes'][0][0]=not c['contract']['summaries'][0]['outcomes'][0][0]
        else:c['contract']['summaries'].append({'call':['x','x',[],0,False,False,False,0,0],'outcomes':[]})
    elif kind==13:
        if c['contract']['summaries']:c['contract']['summaries'][0]['call'][0]+='-forged'
        else:c['contract']['summaries']=[{'call':['x','x',[],0,False,False,False,0,0],'outcomes':[]}]
    elif kind==14:c['comparison']['boundary_equal']=not c['comparison']['boundary_equal']
    elif kind==15:c['comparison']['monolithic_boundary_count']+=1
    elif kind==16:c['comparison']['summary_instances']+=1
    elif kind==17:c['unknown_field']='forbidden'
    elif kind==18:del c['comparison']
    elif kind==19:
        c['monolithic']['states'][0][-2]+=1
    return c

def digest_json(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    t0=time.perf_counter(); fixed=[]; all_models=separation_models()
    for m in all_models:
        r=explore(m); cmp=compare_monolithic_and_contract(m); summ=initial_summary(m)
        assert (not r.unsafe)==m.expected_safe, (m.name,m.expected_safe,not r.unsafe)
        assert cmp['boundary_equal'] and cmp['monolithic_safe']==cmp['contract_safe']
        cert=generate_certificate(m); ok,msg=verify_certificate(m,cert); assert ok,msg
        (CERT/f'{m.name}.json').write_text(json.dumps(cert,indent=2,sort_keys=True)+'\n')
        fixed.append({**cmp,'expected_safe':m.expected_safe,'reachable_states':len(r.states),'reachable_edges':len(r.edges),
                      'initial_summary_outcomes':len(summ),'shortest_bad_trace_events':len(r.shortest_bad_trace())})
    # Pairwise coordinate irreducibility: after dropping the named coordinate, the safe/unsafe summaries coincide.
    irreducibility=[]
    bycoord={}
    for m in all_models:bycoord.setdefault(m.pair_coordinate,[]).append(m)
    for coord,pair in sorted(bycoord.items()):
        pair=sorted(pair,key=lambda m:not bool(m.expected_safe))
        safe=next(m for m in pair if m.expected_safe); unsafe=next(m for m in pair if not m.expected_safe)
        ss={o.project(coord) for o in initial_summary(safe)}; us={o.project(coord) for o in initial_summary(unsafe)}
        assert ss==us and safety_verdict(safe) and not safety_verdict(unsafe)
        irreducibility.append({'coordinate':coord,'safe_model':safe.name,'unsafe_model':unsafe.name,
                               'projected_contract_equal':True,'safe_verdict':True,'unsafe_verdict':False})
    # Exhaustive syntax-space campaign.
    exhaustive=[]
    for i in range(1024):
        m=generated_model(i); cmp=compare_monolithic_and_contract(m); assert cmp['boundary_equal'] and cmp['monolithic_safe']==cmp['contract_safe']
        r=explore(m); exhaustive.append({'id':i,'safe':not r.unsafe,'states':len(r.states),'edges':len(r.edges)})
    # Locked ID and holdout generators. No parameter is fitted on any split.
    random_rows=[]
    for family,start in [('random-id',0),('random-holdout',10000)]:
        for j in range(250):
            m=random_model(start+j,family);cmp=compare_monolithic_and_contract(m);assert cmp['boundary_equal'] and cmp['monolithic_safe']==cmp['contract_safe']
            r=explore(m);random_rows.append({'family':family,'seed':start+j,'safe':not r.unsafe,'states':len(r.states),'edges':len(r.edges)})
    ood_rows=[]
    for j in range(250):
        m=ood_model(j);cmp=compare_monolithic_and_contract(m);assert cmp['boundary_equal'] and cmp['monolithic_safe']==cmp['contract_safe']
        r=explore(m);ood_rows.append({'seed':j,'safe':not r.unsafe,'states':len(r.states),'edges':len(r.edges)})
    # Metamorphic tests on 100 locked bases x 3 semantics-preserving transformations.
    metamorphic=[]
    for j in range(100):
        m=random_model(20000+j,'metamorphic-base');base=safety_verdict(m)
        for label,fn in [('alpha-renaming',rename_model),('transition-permutation',permute_model),('unreachable-extension',unreachable_extension)]:
            mm=fn(m);v=safety_verdict(mm);cmp=compare_monolithic_and_contract(mm);assert v==base and cmp['boundary_equal']
            metamorphic.append({'seed':20000+j,'transform':label,'preserved':True})
    # Independent rational-time oracle: 1,437 fixed judgments.
    oracle_rows=[]
    oracle_models=[generated_model(i) for i in range(1024)] + [random_model(i,'oracle-id') for i in range(250)] + [ood_model(i) for i in range(163)]
    assert len(oracle_models)==1437
    for m in oracle_models:
        a=safety_verdict(m);b=concrete_verdict(m);assert a==b,(m.name,a,b);oracle_rows.append({'model':m.name,'region_safe':a,'rational_oracle_safe':b,'agree':True})
    # 240 systematic certificate mutations: 12 models x 20 mutation operators.
    mutations=[]
    for m in all_models:
        cert=generate_certificate(m)
        for k in range(20):
            ok,msg=verify_certificate(m,mutate(cert,k));assert not ok,(m.name,k)
            mutations.append({'model':m.name,'operator':k,'rejected':True,'reason':msg})
    elapsed=time.perf_counter()-t0
    def dist(rows):
        return {'count':len(rows),'safe':sum(bool(r['safe']) for r in rows),'unsafe':sum(not bool(r['safe']) for r in rows),
                'median_states':statistics.median(r['states'] for r in rows),'max_states':max(r['states'] for r in rows),
                'median_edges':statistics.median(r['edges'] for r in rows),'max_edges':max(r['edges'] for r in rows)}
    summary={
      'schema':'icnc-experiments-v2','fixed_models':len(fixed),'fixed_safe':sum(x['expected_safe'] for x in fixed),'fixed_unsafe':sum(not x['expected_safe'] for x in fixed),
      'irreducibility_coordinates':len(irreducibility),'exhaustive':dist(exhaustive),'random_id':dist([r for r in random_rows if r['family']=='random-id']),
      'random_holdout':dist([r for r in random_rows if r['family']=='random-holdout']),'structural_ood':dist(ood_rows),
      'metamorphic_comparisons':len(metamorphic),'metamorphic_failures':sum(not r['preserved'] for r in metamorphic),
      'oracle_judgments':len(oracle_rows),'oracle_disagreements':sum(not r['agree'] for r in oracle_rows),
      'certificate_mutations':len(mutations),'mutation_acceptances':sum(not r['rejected'] for r in mutations),
      'elapsed_seconds':round(elapsed,6),
      'seed_policy':{'exhaustive':'indices 0..1023','id':'0..249','holdout':'10000..10249','ood':'fixed generator seeds 0..249','metamorphic':'20000..20099','oracle':'declared union'},
      'no_fitted_parameters':True,
    }
    datasets={'fixed_models.json':fixed,'irreducibility.json':irreducibility,'exhaustive.json':exhaustive,'random_splits.json':random_rows,
              'structural_ood.json':ood_rows,'metamorphic.json':metamorphic,'oracle.json':oracle_rows,'mutations.json':mutations,'summary.json':summary}
    for name,obj in datasets.items():(RES/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    manifest={name:hashlib.sha256((RES/name).read_bytes()).hexdigest() for name in datasets}
    (RES/'result-hashes.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__':main()
