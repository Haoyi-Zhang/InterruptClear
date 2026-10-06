#!/usr/bin/env python3
"""Same-model frontier, Boolean configuration-lifting and explicit comparison.

This is an owned implementation of Boolean configuration lifting, not a run
or reproduction of SPLlift, Heros, IFDS/IDE tooling, Blade or CureSpec.
"""
from __future__ import annotations
from collections import Counter
from itertools import product
from pathlib import Path
import argparse
import json
import time
from icnc.runtime_limits import configure_limits,check_cpu_limit,peak_rss_kib
from icnc.model import parse
from icnc.config_lift import build as lift
from icnc.frontier import build as frontier_build, synthesize, unsafe, Meter
from icnc.direct import explore

ROOT = Path(__file__).resolve().parent


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')


def run(primary, output):
    primary = json.loads(Path(primary).read_text())
    details = primary['details']
    if len(details) != 84 or primary['summary']['total_model_instances'] != 84:
        raise AssertionError('comparison requires the current 84 primary model instances')
    family = {row['model']: row['family'] for row in primary['models']}
    family.update({row['expanded_model']: 'lowering' for row in primary['lowerings']})
    counts = Counter()
    comparison_counts = Counter()
    comparator_meter = Meter(limit=200000)
    cpu, wall = time.process_time(), time.monotonic()
    rows = []
    queries = budgets = optimum_checks = 0
    def charge(kind, amount=1):
        check_cpu_limit()
        counts[kind] += amount
        if sum(counts.values()) > 200000:
            raise RuntimeError('configuration comparison campaign ceiling; no verdict')
    for name in sorted(details):
        model = parse(details[name]['model'])
        lifted = lift(model, charge=charge)
        frontier = frontier_build(model, comparator_meter)
        direct = [explore(model, plan, comparator_meter) for plan in range(lifted.plans)]
        if lifted.values.keys() != {state[:6] for value in direct for state in value['reachable']}:
            raise AssertionError((name, 'reachable skeleton disagreement'))
        if len(lifted.values) != frontier['states'] or lifted.edges != frontier['edges']:
            raise AssertionError((name, 'frontier skeleton disagreement'))
        # Compare exact existential marginals at every skeleton state/plan.
        # This does not reconstruct conjunctions of separate may-facts.
        reached_by_plan = [value['reachable'] for value in direct]
        for state, (taint, pending) in lifted.values.items():
            for plan in range(lifted.plans):
                facts = {(v[6], v[7]) for v in reached_by_plan[plan] if v[:6] == state}
                if bool(taint & (1 << plan)) != any(t for t, _ in facts):
                    raise AssertionError((name, state, plan, 'taint interpretation'))
                if bool(pending & (1 << plan)) != any(p for _, p in facts):
                    raise AssertionError((name, state, plan, 'pending interpretation'))
                comparison_counts['fact_state_plan_comparisons'] += 2
        query_rows = []
        for cap in product(*(range(v + 1) for v in model.cap)):
            bits = lifted.truth_at(cap)
            safe = []
            for plan, explicit in enumerate(direct):
                actual = any(all(c <= b for c, b in zip(cost, cap)) for cost in explicit['bad_costs'])
                lifted.counter.add('query_plan_bit_tests')
                answer = bool(bits & (1 << plan))
                if answer != actual or answer != unsafe(frontier['frontier'], plan, cap):
                    raise AssertionError((name, plan, cap, 'plan/budget query'))
                if not actual:
                    safe.append(plan)
                queries += 1
                comparison_counts['three_way_plan_budget_comparisons'] += 1
            opt = lifted.optimum(cap)
            expected = synthesize(model, frontier['frontier'], cap)
            costs = {plan: sum(weight for i, (_, weight) in enumerate(model.atoms) if plan & (1 << i)) for plan in safe}
            best = min(costs.values()) if costs else None
            explicit_opt = {'minimum_cost': best,
                            'optimal_plans': [plan for plan in safe if costs[plan] == best],
                            'safe_plans': len(safe)}
            if opt != expected or opt != explicit_opt:
                raise AssertionError((name, cap, 'exact optimum or tie-set disagreement'))
            query_rows.append({'cap': list(cap), 'unsafe_plan_bits': bits, 'optimum': opt})
            budgets += 1
            optimum_checks += 1
            comparison_counts['three_way_optimal_plan_set_comparisons'] += 1
        fact_vectors = [value for pair in lifted.values.values() for value in pair]
        rows.append({'model': name, 'family': family[name], 'model_input': model.raw(),
                     'plans': lifted.plans, 'cap': list(model.cap),
                     'skeleton_states': len(lifted.values), 'skeleton_edges': lifted.edges,
                     'fact_vector_slots': len(fact_vectors), 'truth_vector_width_bits': lifted.plans,
                     'dense_fact_table_logical_bits': len(fact_vectors) * lifted.plans,
                     'nonzero_fact_vectors': sum(bool(value) for value in fact_vectors),
                     'distinct_fact_vectors': len(set(fact_vectors)),
                     'bad_cost_vectors': len(lifted.bad_by_cost),
                     'frontier_symbolic_proof_terms': frontier['proof_terms'],
                     'frontier_records': len(frontier['frontier']),
                     'explicit_states_summed_over_plans': sum(value['states'] for value in direct),
                     'operations': dict(lifted.counter.counts), 'queries': query_rows})
    if queries != primary['summary']['policy_budget_queries'] or queries != 5046:
        raise AssertionError('primary query inventory changed')
    result = {'schema': 'neutralization-configuration-lifting-comparison',
              'method': 'owned dense Boolean configuration lifting; not external SPLlift reproduction',
              'shared_semantics': ['strict input model', 'one-clock region successor relation'],
              'independent_representation': 'one bit per static plan; no frontier imports in baseline module',
              'summary': {'model_instances': len(rows), 'plan_budget_comparisons': queries,
                          'budget_configurations': budgets, 'optimal_plan_set_comparisons': optimum_checks,
                          'fact_state_plan_comparisons': comparison_counts['fact_state_plan_comparisons'],
                          'mismatches': 0, 'lifting_operations': dict(counts),
                          'comparison_obligations': dict(comparison_counts),
                          'frontier_and_explicit_operations': comparator_meter.counts,
                          'dense_fact_table_logical_bits': sum(row['dense_fact_table_logical_bits'] for row in rows),
                          'fact_vector_slots': sum(row['fact_vector_slots'] for row in rows),
                          'frontier_symbolic_proof_terms': sum(row['frontier_symbolic_proof_terms'] for row in rows),
                          'frontier_records': sum(row['frontier_records'] for row in rows)},
              'models': rows}
    check_cpu_limit()
    measured = {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.monotonic() - wall,
                'peak_rss_kib': peak_rss_kib(), 'workers': 1,
                'meaning': 'whole comparison including all methods; no speedup or per-method timing inference'}
    write(Path(output) / 'reference.json', result)
    write(Path(output) / 'measurements.json', measured)
    return result, measured


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--primary', type=Path, default=ROOT / 'results' / 'primary' / 'reference.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'results' / 'lifting')
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--portable', action='store_true')
    args = parser.parse_args()
    limits = configure_limits(portable=args.portable)
    result, measurements = run(args.primary, args.output)
    measurements['runtime_limits'] = limits
    write(args.output / 'measurements.json', measurements)
    if args.compare is not None and result != json.loads(args.compare.read_text()):
        raise SystemExit('configuration-lifting semantic reproduction differs')
    print(json.dumps({'summary': result['summary'], 'measurements': measurements}, indent=2))
