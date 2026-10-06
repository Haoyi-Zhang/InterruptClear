#!/usr/bin/env python3
"""Frozen finite evaluation of schedule-preserving neutralization repair.

All families and exclusions are fixed here; no generated case is discarded for
its verdict. Timestamps and resource measurements are separate from semantic
results. One worker, standard library only, fail closed at resource ceilings.
"""
from __future__ import annotations
from itertools import product
from pathlib import Path
from dataclasses import replace
from math import comb
import csv,json,time
from icnc.runtime_limits import configure_limits,check_cpu_limit,peak_rss_kib
from icnc.model import parse,initial_state,successors
from icnc.examples import fixed,grammar,threshold,lowering_cases,model,edge,ordering_words
from icnc.frontier import Meter,build,unsafe,synthesize
from icnc.direct import explore
from icnc.checker import check
from icnc.oracle import explore as oracle
from icnc.lowering import expand,projection_obligations
from icnc.word_interpreter import explore as words_explore

ROOT=Path(__file__).resolve().parent

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')

def csvfile(path,rows):
    if not rows:return
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def in_budget(cost,cap):return all(c<=b for c,b in zip(cost,cap))

def labels(frontier,m):
    return [{'cuts':[a for i,(a,_) in enumerate(m.atoms) if mask&(1<<i)],'events':n,'interrupts':k,'peak_depth':h} for mask,n,k,h in frontier]

def longest_events(m,meter):
    # Count physical abstract transition rows as well as base-event cost. Delay
    # arcs have zero row cost; repair slots have one row but zero base-event cost.
    root=initial_state(m);todo=[root];graph={};seen={root}
    while todo:
        s=todo.pop();graph[s]=list(successors(m,s));meter.charge('microstep_bound_arcs',len(graph[s]))
        for _,z,_ in graph[s]:
            if z not in seen:seen.add(z);todo.append(z)
    rank=m.zero_rank;order=sorted(seen,key=lambda s:(s[0],rank[s[3]],s[4],s[1],s[2],s[3],s[5]));values={root:0}
    for s in order:
        for label,z,e in graph[s]:values[z]=max(values.get(z,0),values[s]+(e is not None))
    return max(values.values())

def compare_all(m,result,meter,with_oracle=False):
    rows=[];query_count=0;oracle_cases=0;naive_edges_before=meter.counts.get('explicit_edges',0);base_skeleton=None
    for plan in range(1<<len(m.atoms)):
        d=explore(m,plan,meter)
        structural=(d['structural_states'],d['structural_edges'])
        if base_skeleton is None:base_skeleton=structural
        if structural!=base_skeleton:raise AssertionError('a repair changed the schedule skeleton')
        for cap in product(*(range(x+1) for x in m.cap)):
            actual=any(in_budget(cost,cap) for cost in d['bad_costs'])
            answer=unsafe(result['frontier'],plan,cap)
            meter.charge('policy_budget_query')
            if actual!=answer:raise AssertionError((m.name,plan,cap,'exactness'))
            query_count+=1
        if with_oracle:
            o=oracle(m.raw(),plan,meter.charge)
            if o['bad_costs']!=d['bad_costs'] or o['states']!=d['reachable']:
                raise AssertionError((m.name,plan,'strict DBM oracle disagreement'))
            oracle_cases+=1
        rows.append({'plan':plan,'safe':d['safe'],'explicit_states':d['states'],'bad_costs':[list(x) for x in sorted(d['bad_costs'])]})
    all_atoms=(1<<len(m.atoms))-1
    for record in result['frontier']:
        mask,n,k,h=record; separating_plan=all_atoms^mask; cap=(n,k,h)
        if not unsafe(result['frontier'],separating_plan,cap):raise AssertionError('record separator')
        remainder=tuple(v for v in result['frontier'] if v!=record)
        if unsafe(remainder,separating_plan,cap):raise AssertionError('redundant frontier record')
        meter.charge('irredundancy_separator')
    return rows,query_count,oracle_cases,meter.counts.get('explicit_edges',0)-naive_edges_before

def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    start_cpu=time.process_time();start_wall=time.monotonic();meter=Meter(limit=150000)
    model_rows=[];details={};frontiers={};models={};queries=0;oracles=0
    cases=[('fixed',m) for m in fixed()]+[('finite-grammar',m) for m in grammar()]+[('threshold',threshold(n,n//2)) for n in (2,4,6,8)]
    for family,m in cases:
        before=sum(meter.counts.values());a=build(m,meter);checked=check(m.raw(),a['certificate'],meter.charge)
        oracle_on=family=='fixed' or (family=='threshold' and len(m.atoms)<=4)
        rows,q,o,direct_work=compare_all(m,a,meter,oracle_on); queries+=q;oracles+=o
        opt=synthesize(m,a['frontier'],m.cap)
        direct_safe=[row['plan'] for row in rows if row['safe']]
        costs={x:sum(c for i,(_,c) in enumerate(m.atoms) if x&(1<<i)) for x in direct_safe}
        direct_min=min(costs.values()) if costs else None
        if direct_min!=opt['minimum_cost']:raise AssertionError('direct optimum disagreement')
        if sorted(x for x in direct_safe if costs[x]==direct_min)!=opt['optimal_plans']:raise AssertionError('direct optimal-plan set')
        meter.charge('optimality_comparison',len(rows))
        if family=='threshold':
            n=len(m.atoms);k=n//2
            if len(a['frontier'])!=comb(n,k) or opt['minimum_cost']!=n-k+1:raise AssertionError('threshold theorem')
        actual_rows=longest_events(m,meter)
        if actual_rows>32:raise AssertionError('per-path discrete event cap')
        model_rows.append({'model':m.name,'family':family,'locations':len(m.pcs),'transitions':len(m.edges),'atoms':len(m.atoms),'base_event_cap':m.cap[0],'interrupt_cap':m.cap[1],'depth_cap':m.cap[2],'skeleton_states':a['states'],'skeleton_edges':a['edges'],'proof_terms':a['proof_terms'],'frontier_records':len(a['frontier']),'safe_plans':opt['safe_plans'],'minimum_cost':opt['minimum_cost'],'policy_budget_queries':q,'oracle_plan_instances':o,'explicit_edge_visits_all_plans':direct_work,'longest_discrete_row_path':actual_rows,'charged_work':sum(meter.counts.values())-before})
        details[m.name]={'model':m.raw(),'frontier':labels(a['frontier'],m),'optimum':opt,'plans':rows,'certificate_check':checked}
        frontiers[m.name]=a['frontier'];models[m.name]=m
        if family!='finite-grammar':
            write_json(output/'models'/f'{m.name}.json',m.raw());write_json(output/'certificates'/f'{m.name}.json',a['certificate'])
    # Non-atomic repair-language compilation with real interruption points.
    lowering_rows=[]
    for b,words in lowering_cases():
        m,projection,origins=expand(b,words);projection_obligations(b,m,projection,origins,words)
        a=build(m,meter);checked=check(m.raw(),a['certificate'],meter.charge)
        rows,q,o,work=compare_all(m,a,meter,False);queries+=q;oracles+=o
        phase_index={}
        for baseq in b.pcs:
            ps=[p for p in m.pcs if projection[p]==baseq]
            for j,p in enumerate(ps):phase_index[p]=j
        for plan in range(1<<len(m.atoms)):
            h=words_explore(b,words,plan,meter.charge);d=explore(m,plan,meter)
            extra=oracle(m.raw(),plan,meter.charge)
            if extra['states']!=d['reachable'] or extra['bad_costs']!=d['bad_costs']:
                raise AssertionError('expanded model disagrees with strict DBM oracle')
            converted={(n,k,peak,projection[q],phase_index[q],r,tuple((projection[v],phase_index[v]) for v in stack),t,p) for n,k,peak,q,r,stack,t,p in extra['states']}
            oracles+=1
            if h['states']!=converted or h['bad_costs']!=d['bad_costs']:raise AssertionError('word-language correspondence')
        opt=synthesize(m,a['frontier'],m.cap)
        expected={'L01-drain-clean':2,'L02-clean-drain':None,'L03-clean-repoison':None,'L04-return-repair':4}[b.name]
        if opt['minimum_cost']!=expected:raise AssertionError('word-order negative control')
        actual_rows=longest_events(m,meter)
        if actual_rows>32:raise AssertionError('expanded trace cap')
        lowering_rows.append({'base_model':b.name,'expanded_model':m.name,'word':';'.join(f'{q}:'+','.join(a+':'+bit for a,bit in w) for q,w in words.items()),'locations':len(m.pcs),'transitions':len(m.edges),'skeleton_states':a['states'],'frontier_records':len(a['frontier']),'minimum_cost':opt['minimum_cost'],'safe_plans':opt['safe_plans'],'policy_budget_queries':q,'interpreter_plan_comparisons':1<<len(m.atoms),'longest_discrete_row_path':actual_rows})
        details[m.name]={'model':m.raw(),'frontier':labels(a['frontier'],m),'optimum':opt,'plans':rows,'certificate_check':checked}
        frontiers[m.name]=a['frontier'];models[m.name]=m
        write_json(output/'models'/f'{m.name}.json',m.raw());write_json(output/'certificates'/f'{m.name}.json',a['certificate'])
        write_json(output/'lowerings'/f'{b.name}.json',{'base':b.raw(),'words':words,'expanded':m.raw(),'projection':projection,'edge_origins':origins})
    # A budget-absorption control: ineffective pending clears cannot repair
    # initial taint. Counting their insertion as base events falsely hides use.
    b=model('budget-absorption',['c0','done'],[edge('use','c0','done','use')],[('P',1)],taint=True,cap=(1,0,0))
    m,pr,orig=expand(b,{'c0':[('P','p')]*3});right=build(m,meter)
    wrongraw=m.raw()
    for e in wrongraw['edges']:
        if e['kind']=='repair':e['kind']='nop'
    wrong=parse(wrongraw);a=explore(m,1,meter);d=explore(wrong,1,meter)
    if a['safe'] or not d['safe']:raise AssertionError('vacuity control not discriminating')
    negative={'correct_original_event_safe':a['safe'],'wrong_all_rows_as_events_safe':d['safe'],'original_event_cap':1,'inserted_rows':3,'frontier':labels(right['frontier'],m)}
    write_json(output/'negative-controls.json',negative)
    # Independently exercise the quantified cleanup-order criterion, including
    # repeated operations and absent selected atoms, instead of only PC/CP.
    ordering=[]
    for b,w,letters in ordering_words():
        m,projection,origins=expand(b,w)
        projection_obligations(b,m,projection,origins,w)
        for plan in range(4):
            active=''.join(a for a in letters if plan&(1<<b.atom_index[a]))
            expected=any(a=='P' and 'C' in active[i+1:] for i,a in enumerate(active))
            observed=explore(m,plan,meter)['safe']
            if observed!=expected:raise AssertionError(('cleanup-order law',letters,plan))
            meter.charge('ordering_law_query')
            ordering.append({'word':letters,'plan':plan,'active_word':active,'has_P_before_C':expected,'safe':observed})
    csvfile(output/'cleanup-order.csv',ordering)
    # Actual model copies, including zero-event and zero-delivery boundaries.
    scan=[]
    for original in fixed():
        maxm=original.bounded((8,8,original.cap[2]));fm=build(maxm,meter)
        for n in (1,2,3,4,6,8):
            for k in (0,1,2,4,8):
                active=maxm.bounded((n,k,maxm.cap[2]));d=explore(active,0,meter);pred=unsafe(fm['frontier'],0,active.cap)
                if (not d['safe'])!=pred:raise AssertionError('active budget scan')
                scan.append({'model':original.name,'requested_events':n,'requested_interrupts':k,'effective_events':active.cap[0],'effective_interrupts':active.cap[1],'effective_depth':active.cap[2],'states':d['states'],'safe':d['safe']})
    assert len(scan)==360
    z=[r for r in scan if r['model']=='F03-truncated-handler' and r['effective_interrupts']==0]
    assert all(r['states']==1 and r['safe'] for r in z)
    # Full-domain uniqueness excludes names only; generation changes real
    # actions or initial flags, not merely a label.
    fingerprints=[]
    for m in grammar():
        raw=m.raw();raw.pop('name');fingerprints.append(json.dumps(raw,sort_keys=True))
    if len(set(fingerprints))!=64:raise AssertionError('duplicate executable grammar configuration')
    csvfile(output/'models.csv',model_rows);csvfile(output/'lowering.csv',lowering_rows);csvfile(output/'budget-scan.csv',scan)
    result={'models':model_rows,'lowerings':lowering_rows,'details':details,'negative_controls':negative,'cleanup_order':ordering,'budget_scan':scan,'summary':{'fixed_models':12,'finite_grammar_models':64,'finite_grammar_unique_executable_models':64,'threshold_models':4,'lowering_models':4,'total_model_instances':len(model_rows)+len(lowering_rows),'policy_budget_queries':queries,'oracle_plan_instances':oracles,'oracle_distinct_model_descriptions':18,'budget_configurations':len(scan),'cleanup_word_shapes':31,'cleanup_word_plan_queries':len(ordering),'charged_obligations':meter.counts,'mismatches':0}}
    write_json(output/'reference.json',result)
    check_cpu_limit()
    measurements={'cpu_seconds':time.process_time()-start_cpu,'wall_seconds':time.monotonic()-start_wall,'peak_rss_kib':peak_rss_kib(),'workers':1}
    write_json(output/'measurements.json',measurements)
    return result,measurements
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results'/'primary');ap.add_argument('--compare',type=Path);ap.add_argument('--portable',action='store_true');args=ap.parse_args()
    limits=configure_limits(portable=args.portable)
    result,measures=run(args.output)
    measures['runtime_limits']=limits
    write_json(args.output/'measurements.json',measures)
    if args.compare is not None and result!=json.loads(args.compare.read_text()):raise SystemExit('semantic reproduction differs')
    print(json.dumps({'summary':result['summary'],'measurements':measures},indent=2))
