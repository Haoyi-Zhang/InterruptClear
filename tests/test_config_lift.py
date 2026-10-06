from __future__ import annotations
import ast
from collections import Counter
from itertools import product
from pathlib import Path
import unittest
from icnc.config_lift import build, LiftLimitExceeded
from icnc.direct import explore
from icnc.examples import fixed, threshold, model, edge, lowering_cases
from icnc.lowering import expand

COUNTS = Counter()


def charge(kind, amount=1):
    COUNTS[kind] += amount
    if sum(COUNTS.values()) > 50000:
        raise RuntimeError('configuration test operation ceiling')


class ExplicitTestMeter:
    def charge(self, kind, amount=1):
        charge('test_' + kind, amount)


EXPLICIT = ExplicitTestMeter()


class ConfigurationLifting(unittest.TestCase):
    def test_baseline_imports_no_frontier_or_direct_semantics(self):
        import icnc.config_lift
        tree = ast.parse(Path(icnc.config_lift.__file__).read_text())
        modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(modules, {'__future__', 'collections', 'dataclasses', 'model'})

    def test_fixed_models_all_smaller_budgets(self):
        for m in fixed():
            lifted = build(m, charge=charge)
            for plan in range(lifted.plans):
                actual = explore(m, plan, EXPLICIT)
                for cap in product(*(range(v + 1) for v in m.cap)):
                    expected = any(all(c <= b for c, b in zip(cost, cap)) for cost in actual['bad_costs'])
                    self.assertEqual(lifted.unsafe(plan, cap), expected, (m.name, plan, cap))

    def test_disjunctive_join_preserves_existential_facts(self):
        m = fixed()[11]
        lifted = build(m, charge=charge)
        for state, (taint, pending) in lifted.values.items():
            for plan in range(lifted.plans):
                facts = [(row[6], row[7]) for row in explore(m, plan, EXPLICIT)['reachable'] if row[:6] == state]
                self.assertEqual(bool(taint & (1 << plan)), any(t for t, _ in facts))
                self.assertEqual(bool(pending & (1 << plan)), any(p for _, p in facts))

    def test_preemption_words_and_unreturned_prefix(self):
        expected = [2, None, None, 4]
        for (base, words), best in zip(lowering_cases(), expected):
            m, _, _ = expand(base, words)
            lifted = build(m, charge=charge)
            self.assertEqual(lifted.optimum(m.cap)['minimum_cost'], best)
        m = fixed()[2]
        lifted = build(m, charge=charge)
        self.assertTrue(lifted.unsafe(0, m.cap))
        self.assertFalse(lifted.unsafe(1, m.cap))

    def test_zero_atoms_and_zero_event_boundary(self):
        m = model('no-atoms', ['start', 'done'], [edge('use', 'start', 'done', 'use')], taint=True, cap=(1, 0, 0))
        lifted = build(m, charge=charge)
        self.assertEqual(lifted.plans, 1)
        self.assertEqual(lifted.truth_at((0, 0, 0)), 0)
        self.assertEqual(lifted.truth_at((1, 0, 0)), 1)
        self.assertEqual(lifted.optimum(m.cap), {'minimum_cost': None, 'optimal_plans': [], 'safe_plans': 0})

    def test_resource_tradeoff_is_not_scalarized(self):
        m = fixed()[7]
        lifted = build(m, charge=charge)
        self.assertTrue(lifted.unsafe(2, (2, 1, 1)))
        self.assertFalse(lifted.unsafe(2, (3, 0, 0)))
        self.assertTrue(lifted.unsafe(0, (3, 0, 0)))
        self.assertFalse(lifted.unsafe(0, (2, 0, 0)))

    def test_plan_cap_and_operation_limits_fail_closed(self):
        m = fixed()[0]
        lifted = build(m, charge=charge)
        for plan in (-1, 2, True, '0'):
            with self.assertRaises(ValueError):
                lifted.unsafe(plan, m.cap)
        for cap in ((2, 0, 0), (-1, 0, 0), (True, 0, 0), (1, 0), (1, '0', 0)):
            with self.assertRaises(ValueError):
                lifted.truth_at(cap)
        with self.assertRaises(LiftLimitExceeded):
            build(m, operation_limit=0)
        with self.assertRaises(LiftLimitExceeded):
            build(m, state_limit=1)
        for options in ({'state_limit': 0}, {'state_limit': True}, {'operation_limit': -1}):
            with self.assertRaises(ValueError):
                build(m, **options)

    def test_exact_optimum_ties_and_unused_zero_cost_atom(self):
        m = model('ties', ['start', 'done'], [edge('use', 'start', 'done', 'use', t_clear='C')],
                  [('C', 2), ('unused', 0)], taint=True, cap=(1, 0, 0))
        lifted = build(m, charge=charge)
        self.assertEqual(lifted.optimum(m.cap), {'minimum_cost': 2, 'optimal_plans': [1, 3], 'safe_plans': 2})
        t = threshold(4, 2)
        self.assertEqual(build(t, charge=charge).optimum(t.cap)['minimum_cost'], 3)
