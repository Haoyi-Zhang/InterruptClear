"""Real objective reuse over existing owned models; safety inputs remain fixed."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import query
from icnc.checker import check, Rejected
from icnc.config_lift import build as lift
from icnc.direct import explore
from icnc.examples import fixed, lowering_cases
from icnc.frontier import build, synthesize, unsafe
from icnc.lowering import expand


def ordinary_optimum(m, prices):
    safe = [p for p in range(1 << len(m.atoms)) if explore(m, p)['safe']]
    costs = {p: sum(prices[a] for i,(a,_) in enumerate(m.atoms) if p & (1 << i)) for p in safe}
    best = min(costs.values()) if costs else None
    return {'minimum_cost': best, 'optimal_plans': [p for p in safe if costs[p] == best], 'safe_plans': len(safe)}


class WeightQueries(unittest.TestCase):
    def test_checked_cli_can_reprice_without_replacing_certificate(self):
        m = fixed()[1]
        certificate = build(m)['certificate']
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp) / name for name in ('model.json','certificate.json','weights.json')]
            for path,value in zip(paths, (m.raw(), certificate, {'C':1,'P':2,'U':1})):
                path.write_text(json.dumps(value), encoding='utf-8')
            stream = io.StringIO()
            with patch.object(sys, 'argv', ['query.py', *map(str,paths[:2]), '--weights', str(paths[2])]), redirect_stdout(stream):
                status = query.main()
            answer = json.loads(stream.getvalue())
            self.assertEqual(status, 0)
            self.assertEqual(answer['minimum_cost'], 1)
            self.assertEqual(answer['optimal_plans'], [4])
            self.assertEqual(answer['named_optimal_plans'], [['U']])
            self.assertEqual(json.loads(paths[1].read_text(encoding='utf-8')), certificate)

    def test_zero_prices_retain_all_safe_optimal_supersets(self):
        m = fixed()[1]
        prices = {'C':0,'P':0,'U':0}
        expected = ordinary_optimum(m, prices)
        self.assertEqual(expected['optimal_plans'], [3,4,5,6,7])
        self.assertEqual(synthesize(m,build(m)['frontier'],m.cap,weights=prices), expected)
        self.assertEqual(lift(m).optimum(m.cap,weights=prices), expected)

    def test_weights_must_match_exact_existing_atom_universe_and_type(self):
        m = fixed()[0]
        for weights in ({}, {'C':1,'other':1}, {'C':True}, {'C':1.0}, {'C':-1}, {'C':257}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                synthesize(m,build(m)['frontier'],m.cap,weights=weights)
            with self.subTest(lifting=weights), self.assertRaises(ValueError):
                lift(m).optimum(m.cap,weights=weights)

    def test_repricing_does_not_weaken_trusted_model_equality(self):
        m = fixed()[1]
        result = build(m)
        before = deepcopy(result['certificate'])
        changed = m.raw()
        changed['atoms'][2]['cost'] = 1
        with self.assertRaises(Rejected):
            check(changed,result['certificate'])
        self.assertEqual(synthesize(m,result['frontier'],m.cap,weights={'C':1,'P':2,'U':1})['optimal_plans'], [4])
        self.assertEqual(before,result['certificate'])
        check(m.raw(),result['certificate'])

    def test_same_information_optima_on_all_existing_fixed_and_word_cases(self):
        models = fixed() + [expand(base,words)[0] for base,words in lowering_cases()]
        for m in models:
            prices = {a: len(m.atoms)-i for i,(a,_) in enumerate(m.atoms)}
            expected = ordinary_optimum(m,prices)
            self.assertEqual(synthesize(m,build(m)['frontier'],m.cap,weights=prices),expected,m.name)
            self.assertEqual(lift(m).optimum(m.cap,weights=prices),expected,m.name)

    def test_model_bound_raw_query_refuses_larger_cap_and_unused_plan_bit(self):
        m = fixed()[0]
        frontier = build(m)['frontier']
        with self.assertRaises(ValueError):
            unsafe(frontier,0,(2,0,0),model=m)
        with self.assertRaises(ValueError):
            unsafe(frontier,2,m.cap,model=m)
        self.assertTrue(unsafe(frontier,0,m.cap,model=m))
