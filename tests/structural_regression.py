"""Explicit optional portable tests: literal raw-model finite reference.

No historical code, private paths, campaign drivers, files written or timers.
The reference uses rational region representatives and raw dictionaries rather
than model properties or a producer/checker transition routine.
"""
import sys
import unittest
from collections import deque
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from itertools import product
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
from icnc.model import parse, initial_state, successors, InvalidModel
from icnc.examples import fixed, lowering_cases, threshold
from icnc.lowering import expand, projection_obligations
from icnc.frontier import build, Meter, BudgetExceeded, unsafe, synthesize
from icnc.direct import explore
from icnc.config_lift import build as lift, LiftLimitExceeded
from icnc.checker import check, Rejected
from icnc.oracle import explore as strict_oracle, feasible


def literal(raw, plan):
    constants = raw['constants']
    reps = []
    for i, c in enumerate(constants):
        reps.append(Fraction(c))
        if i + 1 < len(constants):
            reps.append(Fraction(c + constants[i + 1], 2))
    reps.append(Fraction(2 * constants[-1] + 1, 2))
    def truth(region, guards):
        value = reps[region]
        predicates = {'<': lambda c: value < c, '<=': lambda c: value <= c,
                      '==': lambda c: value == c, '>=': lambda c: value >= c,
                      '>': lambda c: value > c}
        return all(predicates[op](c) for op, c in guards)
    atoms = [a['id'] for a in raw['atoms']]
    selected = {a for i, a in enumerate(atoms) if plan & (1 << i)}
    init = raw['initial']
    root = (0, 0, 0, init['pc'], 0, (), init['taint'], init['pending'])
    reached = {root}
    queue = deque([root])
    arcs = set()
    bad = set()
    while queue:
        state = queue.popleft()
        n, k, peak, q, region, stack, taint, pending = state
        next_states = []
        if q not in raw['urgent'] and region + 1 < len(reps) and truth(region + 1, raw['invariants'].get(q, [])):
            next_states.append((('delay', region + 1), (n, k, peak, q, region + 1, stack, taint, pending)))
        for edge in raw['edges']:
            if edge['src'] != q or not truth(region, edge['guard']):
                continue
            action = edge['kind']
            cost = (n + (action != 'repair'), k + (action == 'interrupt'))
            next_stack = stack
            target = edge['dst']
            if action == 'interrupt':
                next_stack += (edge['resume'],)
            if action == 'return':
                if not stack:
                    continue
                target, next_stack = stack[-1], stack[:-1]
            depth = max(peak, len(next_stack))
            if any(v > hi for v, hi in zip((*cost, depth), raw['cap'])):
                continue
            clock = 0 if edge['reset'] else region
            if not truth(clock, raw['invariants'].get(target, [])):
                continue
            t = False if edge['t_clear'] in selected else taint
            p = False if edge['p_clear'] in selected else pending
            if action == 'use' and t:
                bad.add((*cost, depth))
            updates = {'arm': (True, p), 'neutralize': (False, p),
                       'schedule': (t, True), 'clear_pending': (t, False),
                       'commit': (t or p, False)}
            t, p = updates.get(action, (t, p))
            next_states.append((('edge', edge['id']), (*cost, depth, target, clock, next_stack, t, p)))
        for label, target in next_states:
            arcs.add((state[:6], label, target[:6]))
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached, bad, arcs


def models():
    originals = fixed() + [threshold(2, 1), threshold(4, 2)]
    for base, words in lowering_cases():
        phased, projection, origins = expand(base, words)
        if not projection_obligations(base, phased, projection, origins, words):
            raise AssertionError('lowering failed')
        originals.append(phased)
    for original in originals:
        caps = list(dict.fromkeys(((0, 0, 0), original.cap,
                                  tuple(v // 2 for v in original.cap))))
        for cap in caps:
            yield original.bounded(cap)


def observe(m):
    meter = Meter()
    result = build(m, meter)
    checked = check(m.raw(), result['certificate'], meter.charge)
    lifted = lift(m)
    directs = []
    for plan in range(1 << len(m.atoms)):
        direct = explore(m, plan, meter)
        reached, bad, arcs = literal(m.raw(), plan)
        if direct['reachable'] != reached or direct['bad_costs'] != bad or direct['structural_edges'] != arcs:
            raise AssertionError(('literal state/arc/cost mismatch', m.name, plan, m.cap))
        if direct['structural_states'] != {s[:6] for s in reached}:
            raise AssertionError('literal skeleton mismatch')
        for cap in product(*(range(v + 1) for v in m.cap)):
            expected = any(all(v <= b for v, b in zip(cost, cap)) for cost in bad)
            if unsafe(result['frontier'], plan, cap) != expected or lifted.unsafe(plan, cap) != expected:
                raise AssertionError('joint query mismatch')
        directs.append(direct)
    optima = []
    for cap in product(*(range(v + 1) for v in m.cap)):
        safe = [p for p, d in enumerate(directs) if not any(
            all(v <= b for v, b in zip(cost, cap)) for cost in d['bad_costs'])]
        costs = {p: sum(w for i, (_, w) in enumerate(m.atoms) if p & (1 << i)) for p in safe}
        best = min(costs.values()) if costs else None
        expected = {'minimum_cost': best, 'optimal_plans': [p for p in safe if costs[p] == best],
                    'safe_plans': len(safe)}
        if synthesize(m, result['frontier'], cap) != expected or lifted.optimum(cap) != expected:
            raise AssertionError('optimum/ties mismatch')
        optima.append(expected)
    # Complete existential fact/plan projections, not just verdicts.
    for state, (t, p) in lifted.values.items():
        for plan, d in enumerate(directs):
            facts = [(s[6], s[7]) for s in d['reachable'] if s[:6] == state]
            if bool(t & (1 << plan)) != any(x for x, _ in facts) or bool(p & (1 << plan)) != any(y for _, y in facts):
                raise AssertionError('lifted fact mismatch')
    return (m.raw(), result, checked, directs, optima, dict(meter.counts),
            lifted.values, lifted.bad_by_cost, dict(lifted.counter.counts))


def admission_cases():
    base = fixed()[1].raw()
    edits = (lambda r: r.update(extra=True), lambda r: r['cap'].__setitem__(0, True),
             lambda r: r['edges'][0].update(reset='false'),
             lambda r: r['edges'][0].update(kind='and_use'),
             lambda r: r['edges'][0].update(guard=[['taint', 0]]),
             lambda r: r['atoms'][0].update(cost=-1),
             lambda r: r['locations'].extend(['é', 'e\u0301']),
             lambda r: r.update(name='\u0344' * 96),
             lambda r: r['edges'][0].update(kind='repair', dst='c0'))
    for edit in edits:
        raw = deepcopy(base)
        edit(raw)
        yield raw


class StructuralRegression(unittest.TestCase):
    def test_literal_models(self):
        count = 0
        for m in models():
            observe(m)
            count += 1
        self.assertEqual(count, 53)
        self.assertFalse(feasible(2, [(1, 0, 0, True), (0, 1, 0, False)]))
        for m in (fixed()[4], fixed()[5], fixed()[6]):
            for plan in range(2):
                oracle = strict_oracle(m.raw(), plan)
                states, bad, _ = literal(m.raw(), plan)
                self.assertEqual(oracle['states'], states)
                self.assertEqual(oracle['bad_costs'], bad)

    def test_fresh_objects_and_mutable_handbuilt_model(self):
        m = fixed()[1]
        expected = observe(m)
        for prop in ('outgoing', 'atom_index'):
            exposed = getattr(m, prop)
            exposed.clear()
            self.assertNotEqual(getattr(m, prop), exposed)
        timed = fixed()[4]
        original_inv = timed.inv
        exposed = timed.inv
        exposed.clear()
        self.assertEqual(timed.inv, original_inv)
        self.assertIsNot(timed.inv, timed.inv)
        self.assertEqual(observe(m), expected)
        raw = m.raw()
        raw['initial']['taint'] = False
        raw['edges'][0]['t_clear'] = None
        other = parse(raw)
        observe(other)
        self.assertEqual(observe(m), expected)
        # Model is frozen, but manually supplied lists are not: use original
        # fresh reads even after a Meter callback changes a pending guard.
        original = fixed()[0]
        mutable_edge = replace(original.edges[0], guard=[])
        mutable = replace(original, edges=(mutable_edge,))
        class ChangeGuard(Meter):
            def charge(self, kind, n=1):
                super().charge(kind, n)
                if kind == 'explicit_edges':
                    mutable_edge.guard.append(('>', 0))
        first = explore(mutable, 0, ChangeGuard())
        self.assertFalse(first['safe'])
        self.assertTrue(explore(mutable, 0)['safe'])
        mutable_edge.guard.clear()
        self.assertFalse(explore(mutable, 0)['safe'])
        observe(original.bounded((0, 0, 0)))
        self.assertEqual(observe(m), expected)

    def test_admission_and_caps(self):
        for raw in admission_cases():
            with self.assertRaises(InvalidModel):
                parse(raw)
        m = fixed()[0]
        with self.assertRaises(BudgetExceeded):
            build(m, Meter(limit=0))
        with self.assertRaises(LiftLimitExceeded):
            lift(m, operation_limit=0)
        with self.assertRaises(LiftLimitExceeded):
            lift(m, state_limit=1)
        cert = build(m)['certificate']
        cert['nodes'][0]['t'].clear()
        with self.assertRaises(Rejected):
            check(m.raw(), cert)


if __name__ == '__main__':
    unittest.main()
