#!/usr/bin/env python3
"""Deterministic exploratory audit of the supported model-level semantics.

This audit is separate from study.py's fixed primary campaign. The explicit
Boolean explorer shares the producer's region/skeleton implementation. The
strict difference-constraint oracle has a separate time representation, but
shares the intended model specification. Neither check is external review or
a machine-checked proof. All generated cases are retained; any resource ceiling
aborts the audit rather than excluding a model from the reported denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import time
from icnc.runtime_limits import configure_limits,check_cpu_limit,peak_rss_kib
from pathlib import Path

from icnc.checker import check
from icnc.direct import explore
from icnc.examples import edge, model
from icnc.frontier import Meter, build, unsafe
from icnc.oracle import explore as oracle

SEED = 20261005
MODELS = 80
CAP = (4, 2, 2)
ROOT = Path(__file__).resolve().parent


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def generated_models():
    """A fixed seeded bounded grammar; it is not a workload distribution."""
    rng = random.Random(SEED)
    for index in range(MODELS):
        pcs = ['q0', 'q1', 'q2', 'q3']
        edges = []
        for j in range(5):
            src = rng.choice(pcs)
            kind = rng.choice(['nop', 'arm', 'neutralize', 'schedule',
                               'clear_pending', 'commit', 'use',
                               'interrupt', 'return'])
            dst = None if kind == 'return' else rng.choice(pcs)
            resume = rng.choice(pcs) if kind == 'interrupt' else None
            guard = rng.choice([(), (('==', 0),), (('>', 0), ('<', 2)),
                                (('>=', 1),), (('<=', 2),)])
            edges.append(edge(f'e{j}', src, dst, kind, guard=guard,
                              reset=bool(rng.randrange(2)), resume=resume,
                              t_clear=rng.choice([None, 'A', 'B']),
                              p_clear=rng.choice([None, 'B', 'C'])))
        for j in range(rng.randrange(3)):
            a = rng.randrange(3)
            b = rng.randrange(a + 1, 4)
            edges.append(edge(f'r{j}', pcs[a], pcs[b], 'repair',
                              t_clear=rng.choice([None, 'A', 'C']),
                              p_clear=rng.choice([None, 'B'])))
        invariants = {q: [['<=', rng.choice([1, 2])]]
                      for q in pcs if rng.randrange(3) == 0}
        yield model(f'proof-fuzz-{index}', pcs, edges,
                    [('A', 1), ('B', 2), ('C', 0)],
                    taint=bool(rng.randrange(2)),
                    pending=bool(rng.randrange(2)), cap=CAP,
                    constants=(0, 1, 2),
                    urgent=[q for q in pcs if rng.randrange(2)],
                    invariants=invariants)


def run():
    meter = Meter(limit=150000)
    rows = []
    models = []
    totals = {'models': 0, 'plans': 0, 'plan_budget_queries': 0,
              'oracle_state_observations': 0, 'oracle_constraint_systems': 0,
              'oracle_control_prefixes': 0, 'oracle_ceiling_cases': 0,
              'query_disagreements': 0, 'oracle_disagreements': 0}
    for current in generated_models():
        raw = current.raw()
        executable = dict(raw)
        executable.pop('name')
        analysis = build(current, meter)
        check(raw, analysis['certificate'], meter.charge)
        models.append(raw)
        current_rows = []
        totals['models'] += 1
        for plan in range(8):
            direct = explore(current, plan, meter)
            queries = 0
            for cap in itertools.product(range(5), range(3), range(3)):
                expected = any(all(x <= y for x, y in zip(cost, cap))
                               for cost in direct['bad_costs'])
                actual = unsafe(analysis['frontier'], plan, cap)
                meter.charge('audit_plan_budget_query')
                if actual != expected:
                    raise AssertionError(('joint query disagreement',
                                          current.name, plan, cap))
                queries += 1
            independent_time = oracle(raw, plan, meter.charge, limit=100000)
            if (independent_time['states'] != direct['reachable'] or
                    independent_time['bad_costs'] != direct['bad_costs']):
                raise AssertionError(('strict DBM disagreement',
                                      current.name, plan))
            state_rows = sorted(independent_time['states'])
            bad_rows = sorted(independent_time['bad_costs'])
            current_rows.append({
                'plan_mask': plan, 'plan_budget_queries': queries,
                'reachable_boolean_states': len(state_rows),
                'reachable_states_sha256': digest(state_rows),
                'bad_resource_costs': bad_rows,
                'oracle_constraint_systems': independent_time['constraint_systems'],
                'oracle_control_prefixes': independent_time['control_prefixes'],
            })
            totals['plans'] += 1
            totals['plan_budget_queries'] += queries
            totals['oracle_state_observations'] += len(state_rows)
            totals['oracle_constraint_systems'] += independent_time['constraint_systems']
            totals['oracle_control_prefixes'] += independent_time['control_prefixes']
        rows.append({'model_name': current.name,
                     'model_sha256': digest(raw),
                     'executable_description_sha256': digest(executable),
                     'skeleton_states': analysis['states'],
                     'skeleton_edges': analysis['edges'],
                     'frontier': analysis['frontier'],
                     'plans': current_rows})
    expected = {'models': 80, 'plans': 640, 'plan_budget_queries': 28800,
                'oracle_state_observations': 17986,
                'oracle_constraint_systems': 79080,
                'oracle_ceiling_cases': 0, 'query_disagreements': 0,
                'oracle_disagreements': 0}
    for key, value in expected.items():
        if totals[key] != value:
            raise AssertionError(('audit count drift', key, value, totals[key]))
    return {'schema': 'exploratory-semantics-audit', 'seed': SEED,
            'effective_cap': CAP, 'generation_indices': MODELS,
            'unique_executable_descriptions':
                len({row['executable_description_sha256'] for row in rows}),
            'models_sha256': digest(models),
            'evidence_scope': {
                'campaign': 'separate deterministic exploratory audit',
                'primary_campaign_counts_modified': False,
                'direct_explorer_shares_region_skeleton': True,
                'oracle_uses_separate_strict_time_representation': True,
                'oracle_shares_intended_model_specification': True,
                'independent_authorship_or_formal_verification': False,
                'deployment_distribution_or_statistical_generalization': False,
            },
            'totals': totals, 'charged_obligations': meter.counts,
            'models': models, 'model_results': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'results' / 'audit')
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--portable', action='store_true')
    args = parser.parse_args()
    limits = configure_limits(25, 25, 512, portable=args.portable)
    start = time.perf_counter()
    cpu_start = time.process_time()
    result = run()
    check_cpu_limit()
    if args.compare is not None:
        expected = json.loads(args.compare.read_text(encoding='utf-8'))
        if encoded(expected) != encoded(result):
            raise AssertionError('retained exploratory audit differs')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'reference.json').write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + '\n',
        encoding='utf-8')
    measurements = {
        'wall_seconds': time.perf_counter() - start,
        'cpu_seconds': time.process_time() - cpu_start,
        'peak_rss_kib': peak_rss_kib(),
        'runtime_limits': limits,
        'limits': {'cpu_seconds': 25, 'address_space_mib': 512,
                   'charged_obligations': 150000,
                   'oracle_constraints_per_plan': 100000},
        'deterministic_reference_sha256': digest(result),
    }
    (args.out / 'measurements.json').write_text(
        json.dumps(measurements, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    print(json.dumps({'totals': result['totals'],
                      'unique_executable_descriptions': result['unique_executable_descriptions'],
                      'charged_obligations': sum(result['charged_obligations'].values()),
                      'reference_sha256': digest(result)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
