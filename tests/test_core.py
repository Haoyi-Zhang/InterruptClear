import unittest,json,copy,tempfile
from pathlib import Path
import solver,verify,oracle
ROOT=Path(__file__).resolve().parents[1]
GENERATOR_WORK=0
ORACLE_WORK=0
MUTATIONS=0

def solve(id,n=4,k=1):
    global GENERATOR_WORK
    m=solver.load(ROOT/'models'/f'{id}.json');r=solver.explore(m,n,k);GENERATOR_WORK+=r['obligations'];return m,r

class Semantics(unittest.TestCase):
    def test_zero_events_vacuous(self):
        m,r=solve('C03',0,0);self.assertTrue(r['safe']);self.assertEqual(verify.check(m,r['certificate'],0,0)['verdict'],'SAFE')
    def test_use_checked_at_last_admitted_event(self):
        _,before=solve('C07',3,2);_,after=solve('C07',4,2)
        self.assertTrue(before['safe']);self.assertFalse(after['safe']);self.assertEqual(len(after['certificate']['steps']),4)
    def test_nested_failure_seventh_event_exact_oracle(self):
        global ORACLE_WORK
        m,a=solve('C08',7,2);b=oracle.explore(m,7,2);ORACLE_WORK+=b['constraint_systems']
        self.assertFalse(a['safe']);self.assertEqual(a['reachable'],b['reachable']);self.assertFalse(b['safe'])
    def test_delay_does_not_consume_event(self):
        m,r=solve('C03',3,0);self.assertFalse(r['safe']);self.assertEqual(r['certificate']['steps'][1]['x2'],4)
    def test_initial_dirty_is_not_itself_failure(self):
        _,r=solve('A01',1,0);self.assertTrue(r['safe'])
    def test_strict_fractional_witness(self):
        m,r=solve('C05',3,1);self.assertFalse(r['safe']);self.assertEqual(r['certificate']['steps'][1]['x2'],1)
        self.assertEqual(verify.check(m,r['certificate'],3,1)['verdict'],'UNSAFE')
    def test_integer_only_false_safety(self):
        global GENERATOR_WORK
        m,r=solve('C05',4,1);s=solver.explore(m,4,1,integer_only=True);GENERATOR_WORK+=s['obligations'];self.assertTrue(s['safe']);self.assertFalse(r['safe'])
    def test_clean_invariant_not_necessary(self):
        m,r=solve('C06',6,2);self.assertTrue(r['safe']);self.assertTrue(any(q=='h' for n,k,q,x in r['reachable']))
    def test_strict_zero_cycle_infeasible(self):
        self.assertFalse(oracle.feasible(2,[(1,0,0,True),(0,1,0,False)]))
    def test_equal_time_allowed(self):
        self.assertTrue(oracle.feasible(2,[(1,0,0,False),(0,1,0,False)]))
    def test_open_interval_feasible(self):
        self.assertTrue(oracle.feasible(2,[(1,0,1,True),(0,1,0,True)]))
    def test_contradictory_interval_infeasible(self):
        self.assertFalse(oracle.feasible(2,[(1,0,1,True),(0,1,-1,False)]))
    def test_all_small_models_match_exact_oracle(self):
        global ORACLE_WORK
        for id in ['A01','A02','A03','A04','C01','C02','C03','C04','C05','C06','C07','C08']:
            with self.subTest(id=id):
                m,a=solve(id,4,2);b=oracle.explore(m,4,2);ORACLE_WORK+=b['constraint_systems'];self.assertEqual(a['reachable'],b['reachable']);self.assertEqual(a['safe'],b['safe'])

class Certificates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m,cls.r=solve('A01',4,1)
    def rejected(self,c,m=None):
        global MUTATIONS
        MUTATIONS+=1
        with self.assertRaises(verify.Rejected):verify.check(self.m if m is None else m,c,4,1)
    def copy(self):return copy.deepcopy(self.r['certificate'])
    def test_valid(self):self.assertEqual(verify.check(self.m,self.copy(),4,1)['verdict'],'SAFE')
    def test_missing_initial(self):
        c=self.copy();c['states']=[s for s in c['states'] if s[0]!=0];self.rejected(c)
    def test_missing_successor(self):
        c=self.copy();c['states']=[s for s in c['states'] if s[0]!=2];self.rejected(c)
    def test_duplicate_state(self):
        c=self.copy();c['states'].append(c['states'][0]);self.rejected(c)
    def test_boolean_count(self):
        c=self.copy();c['states'][0][0]=False;self.rejected(c)
    def test_negative_count(self):
        c=self.copy();c['states'][0][0]=-1;self.rejected(c)
    def test_out_of_range_region(self):
        c=self.copy();c['states'][0][3]=2;self.rejected(c)
    def test_unknown_location(self):
        c=self.copy();c['states'][0][2]='absent';self.rejected(c)
    def test_wrong_model_id(self):
        c=self.copy();c['model']='different';self.rejected(c)
    def test_event_budget_substitution(self):
        c=self.copy();c['events']=3;self.rejected(c)
    def test_interrupt_budget_substitution(self):
        c=self.copy();c['interrupts']=0;self.rejected(c)
    def test_boolean_budget(self):
        c=self.copy();c['interrupts']=True;self.rejected(c)
    def test_unknown_fields(self):
        c=self.copy();c['edges']=[];self.rejected(c)
    def test_invalid_kind(self):
        c=self.copy();c['kind']='trust_me';self.rejected(c)
    def test_trusted_model_reenumerated(self):
        m=copy.deepcopy(self.m);m['edges'].append({'id':'new','src':'d','dst':'d','kind':'use','guard':[],'reset':False});self.rejected(self.copy(),m)
    def test_bad_neutralization_annotation(self):
        m=copy.deepcopy(self.m);m['nodes'][1]['clean']=False;self.rejected(self.copy(),m)
    def test_redundant_boundary_state_allowed(self):
        c=self.copy();extra=[4,0,'d',1]
        if extra not in c['states']:c['states'].append(extra)
        self.assertEqual(verify.check(self.m,c,4,1)['verdict'],'SAFE')
    def test_duplicate_json_key(self):
        global MUTATIONS
        MUTATIONS+=1
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(verify.Rejected):verify.read_json(p,200)
    def test_nonfinite_json(self):
        global MUTATIONS
        MUTATIONS+=1
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"a":NaN}')
            with self.assertRaises(verify.Rejected):verify.read_json(p,200)
    def test_input_byte_limit(self):
        global MUTATIONS
        MUTATIONS+=1
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"a":1}')
            with self.assertRaises(verify.Rejected):verify.read_json(p,3)
    def test_diagnostic_without_failure_rejected(self):
        global MUTATIONS
        MUTATIONS+=1;m,r=solve('C05',4,1);c=copy.deepcopy(r['certificate']);c['steps']=c['steps'][:1]
        with self.assertRaises(verify.Rejected):verify.check(m,c,4,1)
    def test_diagnostic_invalid_clock_rejected(self):
        global MUTATIONS
        MUTATIONS+=1;m,r=solve('C05',4,1);c=copy.deepcopy(r['certificate']);c['steps'][1]['x2']=0
        with self.assertRaises(verify.Rejected):verify.check(m,c,4,1)
    def test_diagnostic_wrong_edge_rejected(self):
        global MUTATIONS
        MUTATIONS+=1;m,r=solve('C05',4,1);c=copy.deepcopy(r['certificate']);c['steps'][0]['edge']='missing'
        with self.assertRaises(verify.Rejected):verify.check(m,c,4,1)
    def test_diagnostic_boolean_time_rejected(self):
        global MUTATIONS
        MUTATIONS+=1;m,r=solve('C05',4,1);c=copy.deepcopy(r['certificate']);c['steps'][1]['x2']=True
        with self.assertRaises(verify.Rejected):verify.check(m,c,4,1)
