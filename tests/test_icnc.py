from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from copy import deepcopy
from icnc.generators import separation_models, generated_model, random_model, ood_model, rename_model, permute_model, unreachable_extension
from icnc.model import model_from_dict, ModelError, load_model
from icnc.semantics import safety_verdict, explore, initial_state
from icnc.contract import compare_monolithic_and_contract, episode_outcomes
from icnc.certificate import generate_certificate, verify_certificate, strict_json_load, CertificateError
from icnc.oracle import concrete_verdict

MODELS=separation_models()
class VerdictTests(unittest.TestCase): pass
for i,m in enumerate(MODELS):
    def f(self,m=m): self.assertEqual(safety_verdict(m),m.expected_safe)
    setattr(VerdictTests,f'test_{i:02d}_{m.name.replace("-","_")}',f)

class CompositionTests(unittest.TestCase): pass
for i,m in enumerate(MODELS):
    def f(self,m=m):
        c=compare_monolithic_and_contract(m);self.assertTrue(c['boundary_equal']);self.assertEqual(c['monolithic_safe'],c['contract_safe'])
    setattr(CompositionTests,f'test_{i:02d}_{m.name.replace("-","_")}',f)

class IrreducibilityTests(unittest.TestCase): pass
_coords=sorted({m.pair_coordinate for m in MODELS})
for i,coord in enumerate(_coords):
    def f(self,coord=coord):
        pair=[m for m in MODELS if m.pair_coordinate==coord];s=next(m for m in pair if m.expected_safe);u=next(m for m in pair if not m.expected_safe)
        def summ(m):
            st=initial_state(m);call=next(t for t in m.outgoing(st.pc) if t.event=='interrupt');return {o.project(coord) for o in episode_outcomes(m,st,call)}
        self.assertEqual(summ(s),summ(u));self.assertNotEqual(safety_verdict(s),safety_verdict(u))
    setattr(IrreducibilityTests,f'test_{i:02d}_{coord}',f)

class ExhaustiveSamples(unittest.TestCase): pass
for i,n in enumerate([0,1,3,7,31,63,127,255,511,1023]):
    def f(self,n=n):
        m=generated_model(n);c=compare_monolithic_and_contract(m);self.assertTrue(c['boundary_equal']);self.assertEqual(c['monolithic_safe'],c['contract_safe'])
    setattr(ExhaustiveSamples,f'test_{i:02d}_model_{n}',f)

class RobustnessTests(unittest.TestCase):
    def test_unknown_model_field(self):
        d=MODELS[0].canonical_dict();d['forged']=1
        with self.assertRaises(ModelError):model_from_dict(d)
    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(CertificateError):strict_json_load(p)
    def test_unknown_certificate_field(self):
        m=MODELS[0];c=generate_certificate(m);c['forged']=1;self.assertFalse(verify_certificate(m,c)[0])
    def test_deleted_certificate_state(self):
        m=MODELS[0];c=generate_certificate(m);c['monolithic']['states']=c['monolithic']['states'][1:];self.assertFalse(verify_certificate(m,c)[0])
    def test_forged_summary(self):
        m=MODELS[0];c=generate_certificate(m);c['contract']['summaries'][0]['outcomes'][0][0]=not c['contract']['summaries'][0]['outcomes'][0][0];self.assertFalse(verify_certificate(m,c)[0])
    def test_model_hash_binds_certificate(self):
        a,b=MODELS[:2];self.assertFalse(verify_certificate(b,generate_certificate(a))[0])

class MetamorphicTests(unittest.TestCase):
    def test_alpha_renaming(self):
        m=random_model(55);self.assertEqual(safety_verdict(m),safety_verdict(rename_model(m)))
    def test_transition_permutation(self):
        m=random_model(56);self.assertEqual(safety_verdict(m),safety_verdict(permute_model(m)))
    def test_unreachable_extension(self):
        m=random_model(57);self.assertEqual(safety_verdict(m),safety_verdict(unreachable_extension(m)))

class OracleTests(unittest.TestCase): pass
for i,m in enumerate([generated_model(9),generated_model(777),random_model(2),random_model(99),ood_model(1),ood_model(42)]):
    def f(self,m=m):self.assertEqual(safety_verdict(m),concrete_verdict(m))
    setattr(OracleTests,f'test_{i:02d}_{m.name}',f)
