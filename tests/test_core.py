from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
from itertools import product
from math import comb
from icnc.model import parse,read,InvalidModel
from icnc.examples import fixed,threshold,model,edge,grammar,lowering_cases,ordering_words
from icnc.frontier import build,unsafe,synthesize,Meter,reduce_frontier
from icnc.direct import explore
from icnc.checker import check,Rejected
from icnc.oracle import explore as oracle,feasible
from icnc.lowering import expand,projection_obligations
from icnc.word_interpreter import explore as high
from icnc import runtime_limits
from unittest.mock import patch

METER=Meter(limit=90000)

def compare(m):
 a=build(m,METER); check(m.raw(),a['certificate'],METER.charge)
 for x in range(1<<len(m.atoms)):
  d=explore(m,x,METER)
  for b in product(*(range(v+1) for v in m.cap)):
   actual=any(all(u<=v for u,v in zip(c,b)) for c in d['bad_costs'])
   METER.charge('test_query')
   if unsafe(a['frontier'],x,b)!=actual:raise AssertionError((m.name,x,b))
 return a

class Semantics(unittest.TestCase):
 pass
for idx in range(12):
 def test(self,idx=idx): compare(fixed()[idx])
 setattr(Semantics,f'test_fixed_{idx+1:02d}',test)

class Theorems(unittest.TestCase):
 def test_every_finite_grammar_case(self):
  signatures=[]
  for m in grammar():
   compare(m);raw=m.raw();raw.pop('name');signatures.append(json.dumps(raw,sort_keys=True))
  self.assertEqual(len(signatures),len(set(signatures)));self.assertEqual(len(signatures),64)
 def test_threshold_lower_bound(self):
  for n in (2,4,6,8):
   m=threshold(n,n//2);a=compare(m)
   self.assertEqual(len(a['frontier']),comb(n,n//2))
   self.assertEqual(synthesize(m,a['frontier'],m.cap)['minimum_cost'],n-n//2+1)
 def test_irredundant_query_separators(self):
  for m in fixed()+[threshold(6,3)]:
   a=build(m,METER);full=(1<<len(m.atoms))-1
   for row in a['frontier']:
    x=full^row[0];b=row[1:]
    self.assertTrue(unsafe(a['frontier'],x,b))
    self.assertFalse(unsafe([v for v in a['frontier'] if v!=row],x,b))
 def test_frontier_canonical_reduction(self):
  raw=[(1,3,1,1),(3,4,1,1),(1,3,1,1),(2,2,1,1)]
  self.assertEqual(reduce_frontier(raw),((1,3,1,1),(2,2,1,1)))
  self.assertEqual(reduce_frontier(reversed(raw)),reduce_frontier(raw))
 def test_budget_tradeoff_not_scalar(self):
  m=fixed()[7];a=build(m,METER)
  self.assertEqual(a['frontier'],((1,2,1,1),(2,3,0,0)))
  self.assertTrue(unsafe(a['frontier'],2,(2,1,1)))
  self.assertFalse(unsafe(a['frontier'],2,(3,0,0)))
 def test_truncated_bad_prefix_is_observed(self):
  m=fixed()[2];a=build(m,METER);self.assertEqual(a['frontier'],((1,2,1,1),))
  self.assertTrue(unsafe(a['frontier'],0,(2,1,1)))
  self.assertFalse(any(not st[5] and st[0]>0 for st in explore(m,0,METER)['structural_states']))
 def test_budget_zero_and_monotonicity(self):
  m=fixed()[2];a=build(m,METER)
  self.assertTrue(explore(m.bounded((2,0,1)),0,METER)['safe'])
  self.assertTrue(explore(m.bounded((0,1,1)),0,METER)['safe'])
  for x in range(2):
   for n in range(4):
    b=m.bounded((n,1,1));d=explore(b,x,METER)
    self.assertEqual(not d['safe'],unsafe(a['frontier'],x,(min(n,2),1,1)))
 def test_typed_transition_label_collision(self):
  a=fixed()[4];raw=a.raw();raw['name']='ordinary-ID';raw['edges'][0]['id']='call';b=parse(raw)
  for x in (0,1):
   da=explore(a,x,METER);db=explore(b,x,METER)
   self.assertEqual(da['reachable'],db['reachable'])
  self.assertEqual(build(a,METER)['frontier'],build(b,METER)['frontier'])
 def test_strict_oracle_all_fixed_plans(self):
  for m in fixed():
   for x in range(1<<len(m.atoms)):
    a=oracle(m.raw(),x,METER.charge);b=explore(m,x,METER)
    self.assertEqual(a['states'],b['reachable']);self.assertEqual(a['bad_costs'],b['bad_costs'])
 def test_dbm_strict_zero_cycle(self):
  self.assertFalse(feasible(2,[(1,0,0,True),(0,1,0,False)]))
  self.assertTrue(feasible(2,[(1,0,1,True),(0,1,0,True)]))
 def test_weighted_optimum_not_greedy(self):
  m=fixed()[10];a=build(m,METER);o=synthesize(m,a['frontier'],m.cap)
  self.assertEqual(o['minimum_cost'],2);self.assertEqual(o['optimal_plans'],[5])
 def test_empty_obstruction_means_unrepairable(self):
  m=fixed()[9];a=build(m,METER);self.assertEqual(synthesize(m,a['frontier'],m.cap)['minimum_cost'],None)
 def test_and_transfer_rejected_not_silently_approximated(self):
  raw=fixed()[11].raw();raw['edges'][-1]['kind']='and_use'
  with self.assertRaises(InvalidModel):parse(raw)

class Lowering(unittest.TestCase):
 def test_all_word_cases_semantically_match(self):
  for b,word in lowering_cases():
   m,projection,origin=expand(b,word);self.assertTrue(projection_obligations(b,m,projection,origin,word));compare(m)
   for x in range(1<<len(m.atoms)):
    h=high(b,word,x,METER.charge);d=explore(m,x,METER)
    phases={q:j for baseq in b.pcs for j,q in enumerate(p for p in m.pcs if projection[p]==baseq)}
    mapped={(n,k,peak,projection[q],phases[q],r,tuple((projection[v],phases[v]) for v in st),t,p)
            for n,k,peak,q,r,st,t,p in d['reachable']}
    self.assertEqual(h['bad_costs'],d['bad_costs']);self.assertEqual(h['states'],mapped)
 def test_declaration_required_and_instrumented_base_rejected(self):
  b,w=lowering_cases()[0];m,p,o=expand(b,w)
  with self.assertRaises(ValueError):projection_obligations(b,m,p,o)
  raw=b.raw();raw['edges'][0]['t_clear']='C';instrumented=parse(raw)
  with self.assertRaises(ValueError):expand(instrumented,w)
  with self.assertRaises(ValueError):projection_obligations(instrumented,m,p,o,w)
  raw=b.raw();raw['edges'][0]['kind']='repair';instrumented=parse(raw)
  with self.assertRaises(ValueError):expand(instrumented,w)
  with self.assertRaises(ValueError):projection_obligations(instrumented,m,p,o,w)
 def test_clear_order_changes_synthesizability(self):
  outcomes=[]
  for b,w in lowering_cases()[:2]:
   m,_,_=expand(b,w);a=build(m,METER);outcomes.append(synthesize(m,a['frontier'],m.cap)['minimum_cost'])
  self.assertEqual(outcomes,[2,None])
 def test_ineffective_repair_cannot_consume_base_budget(self):
  b=model('bad',['c0','done'],[edge('u','c0','done','use')],[('P',1)],taint=True,cap=(1,0,0))
  m,_,_=expand(b,{'c0':[('P','p')]*3});self.assertFalse(explore(m,1,METER)['safe'])
  raw=m.raw()
  for e in raw['edges']:
   if e['kind']=='repair':e['kind']='nop'
  self.assertTrue(explore(parse(raw),1,METER)['safe'])
 def test_missing_interrupt_phase_is_rejected(self):
  b,w=lowering_cases()[0];m,p,o=expand(b,w);raw=m.raw()
  i=next(i for i,e in enumerate(raw['edges']) if e['kind']=='interrupt');del raw['edges'][i];bad=parse(raw)
  with self.assertRaises(ValueError):projection_obligations(b,bad,p,o,w)
 def test_swapped_clear_word_is_rejected(self):
  b,w=lowering_cases()[0];m,p,o=expand(b,w)
  with self.assertRaises(ValueError):projection_obligations(b,m,p,o,{'c1':list(reversed(w['c1']))})
 def test_changed_clock_reset_rejected(self):
  b,w=lowering_cases()[0];m,p,o=expand(b,w);raw=m.raw()
  e=next(e for e in raw['edges'] if e['kind']=='interrupt');e['reset']=True;bad=parse(raw)
  with self.assertRaises(ValueError):projection_obligations(b,bad,p,o,w)
 def test_changed_initial_fact_rejected(self):
  b,w=lowering_cases()[0];m,p,o=expand(b,w);raw=m.raw();raw['initial']['taint']=not raw['initial']['taint'];bad=parse(raw)
  with self.assertRaises(ValueError):projection_obligations(b,bad,p,o,w)
 def test_untrusted_lowering_word_and_annotation_domains_rejected(self):
  b=model('invalid-word',['c0','done'],[edge('use','c0','done','use')],[('P',1)],pending=True,cap=(1,0,0))
  m,p,o=expand(b,{'c0':[('P','p')]});raw=m.raw()
  for e in raw['edges']:
   if e['kind']=='repair':e['p_clear']=None
  identity=parse(raw)
  for badword in ({'c0':[('P','invalid')]},{'missing':[]},{'c0':[('P',)]},{'c0':[('P',True)]},{'c0':[('missing','p')]},{'c0':['Pp']}):
   with self.subTest(word=badword),self.assertRaises(ValueError):projection_obligations(b,identity,p,o,badword)
   with self.subTest(generator_word=badword),self.assertRaises(ValueError):expand(b,badword)
  with self.assertRaises(ValueError):projection_obligations(b,m,p,{**o,'missing':None},{'c0':[('P','p')]})
  with self.assertRaises(ValueError):projection_obligations(b,m,{**p,m.initial:'missing'},o,{'c0':[('P','p')]})
 def test_zero_event_cycle_rejected(self):
  raw=fixed()[0].raw();e=raw['edges'][0];e['kind']='repair';e['dst']=e['src']
  with self.assertRaises(InvalidModel):parse(raw)
 def test_selected_plan_does_not_change_schedules(self):
  b,w=lowering_cases()[0];m,_,_=expand(b,w);first=explore(m,0,METER)
  for x in range(1<<len(m.atoms)):
   d=explore(m,x,METER);self.assertEqual(first['structural_states'],d['structural_states']);self.assertEqual(first['structural_edges'],d['structural_edges'])

class AdditionalProofObligations(unittest.TestCase):
 def test_ordering_criterion_all_words_length_at_most_four(self):
  count=0
  for b,w,letters in ordering_words():
   m,p,o=expand(b,w);projection_obligations(b,m,p,o,w)
   for plan in range(4):
    active=''.join(a for a in letters if plan&(1<<b.atom_index[a]))
    expected=any(a=='P' and 'C' in active[i+1:] for i,a in enumerate(active))
    self.assertEqual(explore(m,plan,METER)['safe'],expected,(letters,plan));count+=1
  self.assertEqual(count,124)
 def test_peak_depth_not_depth_at_use(self):
  m=fixed()[8];a=build(m,METER)
  self.assertTrue(unsafe(a['frontier'],0,(6,2,2)))
  self.assertFalse(unsafe(a['frontier'],0,(6,2,1)))
  bad_states=[s for s in explore(m,0,METER)['reachable'] if s[0]==6]
  self.assertTrue(any(s[2]==2 and len(s[5])==1 for s in bad_states))
 def test_optimal_plan_set_against_explicit_execution(self):
  for m in fixed():
   a=build(m,METER);safe=[p for p in range(1<<len(m.atoms)) if explore(m,p,METER)['safe']]
   costs={p:sum(c for i,(_,c) in enumerate(m.atoms) if p&(1<<i)) for p in safe}
   best=min(costs.values()) if costs else None;result=synthesize(m,a['frontier'],m.cap)
   self.assertEqual(best,result['minimum_cost'])
   self.assertEqual(sorted(p for p in safe if costs[p]==best),result['optimal_plans'])

class Parsing(unittest.TestCase):
 def test_portable_limits_report_missing_capabilities(self):
  with patch.object(runtime_limits,'_resource',None),patch.object(runtime_limits,'_cpu_deadline',None):
   with self.assertRaises(RuntimeError):runtime_limits.configure_limits()
   report=runtime_limits.configure_limits(1,2,512,portable=True)
   self.assertFalse(report['os_cpu_limit_enforced']);self.assertFalse(report['os_address_space_limit_enforced'])
   self.assertEqual(report['mode'],'portable');self.assertIsNone(runtime_limits.peak_rss_kib())
   with patch.object(runtime_limits.time,'process_time',return_value=2):
    with self.assertRaises(RuntimeError):runtime_limits.check_cpu_limit()
 def reject(self,mutate):
  raw=fixed()[1].raw();mutate(raw)
  with self.assertRaises((InvalidModel,TypeError)):parse(raw)
 def test_reset_string(self):self.reject(lambda d:d['edges'][0].update(reset='false'))
 def test_numeric_identifier(self):self.reject(lambda d:d['edges'][0].update(id=1))
 def test_boolean_integer(self):self.reject(lambda d:d['cap'].__setitem__(0,True))
 def test_normalized_collision(self):self.reject(lambda d:d['locations'].extend(['é','e\u0301']))
 def test_normalized_identifier_expansion_rejected_and_legal_roundtrip(self):
  raw=fixed()[0].raw();raw['name']='\u0344'*96
  with self.assertRaises(InvalidModel):parse(raw)
  with self.assertRaises(Rejected):check(raw,build(fixed()[0],METER)['certificate'],METER.charge)
  raw['name']='e\u0301';legal=parse(raw)
  self.assertEqual(legal.name,'é');self.assertEqual(parse(legal.raw()),legal)
  check(raw,build(legal,METER)['certificate'],METER.charge)
 def test_unknown_guard(self):self.reject(lambda d:d['edges'][0].update(guard=[['taint',0]]))
 def test_unknown_field(self):self.reject(lambda d:d.update(secret_guard=True))
 def test_negative_cost(self):self.reject(lambda d:d['atoms'][0].update(cost=-1))
 def test_nontotal_repair_guard(self):self.reject(lambda d:d['edges'][0].update(kind='repair',guard=[['==',0]]))
 def test_roundtrip(self):
  for m in fixed():self.assertEqual(parse(m.raw()),m)
 def test_duplicate_json_keys(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'x.json';p.write_text('{"a":1,"a":2}')
   with self.assertRaises(InvalidModel):read(p)

class Certificates(unittest.TestCase):
 def test_no_import_of_generator_or_region_explorer(self):
  import ast,icnc.checker
  tree=ast.parse(Path(icnc.checker.__file__).read_text())
  mods={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
  self.assertTrue(mods<={'__future__','pathlib'})
 def test_systematic_mutations(self):
  m=fixed()[1];cert=build(m,METER)['certificate']
  transforms=[lambda c:c.update(schema='other'),lambda c:c.update(extra=True),lambda c:c['model']['initial'].update(taint=False),lambda c:c['nodes'].pop(),lambda c:c['nodes'][0]['state'].__setitem__(0,1),lambda c:c['nodes'][1]['parent'].__setitem__(0,1),lambda c:c['nodes'][1]['parent'][1].__setitem__(1,'missing'),lambda c:c['nodes'][0]['t'].clear(),lambda c:c['nodes'][0]['t'].append(0),lambda c:c['nodes'][0]['t'].__setitem__(0,True),lambda c:c['frontier'].pop(),lambda c:c['frontier'].append([0,1,0,0]),lambda c:c['frontier'][0].__setitem__(0,0),lambda c:c['frontier'][0].__setitem__(1,0),lambda c:c['nodes'][0].update(bad=False),lambda c:c['nodes'][0]['state'].__setitem__(3,'missing'),lambda c:c['nodes'][0]['state'].__setitem__(4,100),lambda c:c['nodes'][0]['p'].append(1),lambda c:c['nodes'][1]['state'].__setitem__(5,['c0']),lambda c:c['nodes'][1].update(parent=None)]
  for i,mut in enumerate(transforms):
   c=copy.deepcopy(cert);mut(c)
   with self.subTest(index=i),self.assertRaises((Rejected,TypeError,KeyError,IndexError)):check(m.raw(),c,METER.charge)
  self.assertEqual(len(transforms),20)
 def test_nonminimal_and_duplicate_frontier_rejected(self):
  m=fixed()[0];c=build(m,METER)['certificate'];c['frontier'].append(c['frontier'][0][:])
  with self.assertRaises(Rejected):check(m.raw(),c,METER.charge)
 def test_corrupted_certificate_does_not_change_trusted_model(self):
  m=fixed()[9];c=build(m,METER)['certificate'];c['model']['edges'][-1]['kind']='nop'
  with self.assertRaises(Rejected):check(m.raw(),c,METER.charge)

if __name__=='__main__':unittest.main()
