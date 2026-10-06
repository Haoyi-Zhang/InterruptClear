#!/usr/bin/env python3
"""Clean semantic reproduction and replay; status is emitted only after checks."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from icnc.checker import check, read
from icnc.lowering import projection_obligations
from icnc.model import parse
from icnc.runtime_limits import configure_limits,check_cpu_limit
from run_tests import EXPECTED_TEST_METHODS

ROOT = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'results' / 'verification.json')
    ap.add_argument('--portable', action='store_true')
    ap.add_argument('--scratch', type=Path, default=ROOT / 'results' / 'scratch')
    args = ap.parse_args()
    limits = configure_limits(portable=args.portable)
    start = time.monotonic()
    env = dict(os.environ, PYTHONHASHSEED='0')
    args.scratch.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(args.scratch.resolve()), TMP=str(args.scratch.resolve()), PYTHONDONTWRITEBYTECODE='1')
    portable = ['--portable'] if args.portable else []
    counts = {}
    def charge(kind, amount=1):
        check_cpu_limit()
        counts[kind] = counts.get(kind, 0) + amount
        if sum(counts.values()) > 100000:
            raise RuntimeError('verification work ceiling; no verdict')
    with tempfile.TemporaryDirectory(prefix='neutralization-reproduction-', dir=args.scratch) as temp:
        temp = Path(temp)
        testfile = temp / 'tests.json'
        subprocess.run([sys.executable, str(ROOT / 'run_tests.py'), '--output', str(testfile), *portable], cwd=ROOT, env=env, check=True, timeout=190)
        test = json.loads(testfile.read_text())
        if test['test_methods'] != EXPECTED_TEST_METHODS or not test['successful'] or test['failures'] or test['errors'] or test['skips']:
            raise RuntimeError('test result mismatch')
        fresh = temp / 'study'
        subprocess.run([sys.executable, str(ROOT / 'study.py'), '--output', str(fresh), '--compare', str(ROOT / 'results' / 'primary' / 'reference.json'), *portable], cwd=ROOT, env=env, check=True, timeout=190)
        original = ROOT / 'results' / 'primary'
        observed = json.loads((fresh / 'reference.json').read_text())
        audit_directory = temp / 'semantic-audit'
        subprocess.run([sys.executable, str(ROOT / 'audit_semantics.py'), '--out', str(audit_directory), '--compare', str(ROOT / 'results' / 'audit' / 'reference.json'), *portable], cwd=ROOT, env=env, check=True, timeout=40)
        audit = json.loads((audit_directory / 'reference.json').read_text())
        lifting_directory = temp / 'configuration-lifting'
        subprocess.run([sys.executable, str(ROOT / 'compare_lifting.py'), '--primary', str(fresh / 'reference.json'), '--output', str(lifting_directory), '--compare', str(ROOT / 'results' / 'lifting' / 'reference.json'), *portable], cwd=ROOT, env=env, check=True, timeout=190)
        lifting = json.loads((lifting_directory / 'reference.json').read_text())
        # Exact retained model/certificate bytes are not cryptographic evidence;
        # compare parsed scientific values instead of generating hash manifests.
        for folder in ('models', 'certificates', 'lowerings'):
            a = {p.name for p in (original / folder).glob('*.json')}
            b = {p.name for p in (fresh / folder).glob('*.json')}
            if a != b:
                raise RuntimeError('retained file set differs: ' + folder)
            for name in a:
                if json.loads((original / folder / name).read_text()) != json.loads((fresh / folder / name).read_text()):
                    raise RuntimeError('scientific artifact differs: ' + name)
        replay = []
        for path in sorted((fresh / 'models').glob('*.json')):
            raw = read(path)
            result = check(raw, read(fresh / 'certificates' / path.name), charge)
            replay.append({'model': raw['name'], 'check': result})
        lowerings = []
        for path in sorted((fresh / 'lowerings').glob('*.json')):
            row = json.loads(path.read_text())
            result = projection_obligations(parse(row['base']), parse(row['expanded']), row['projection'], row['edge_origins'], row['words'])
            if result is not True:
                raise RuntimeError('lowering proof failed')
            lowerings.append(row['base']['name'])
        if len(replay) != 20 or len(lowerings) != 4:
            raise RuntimeError('evidence inventory incomplete')
        campaign_operations = {
            'tests': sum(test['charged_operations'].values()),
            'primary_study': sum(observed['summary']['charged_obligations'].values()),
            'separate_semantic_audit': sum(audit['charged_obligations'].values()),
            'configuration_lifting_comparison': sum(sum(lifting['summary'][field].values()) for field in ('lifting_operations', 'comparison_obligations', 'frontier_and_explicit_operations')),
            'retained_certificate_replay': sum(counts.values()),
        }
        total = sum(campaign_operations.values())
        if total > 400000:
            raise RuntimeError('aggregate reproduction allowance exceeded')
        report = {
            'status': 'PASS',
            'meaning': 'all listed commands and finite equalities completed; not a proof-assistant result or publication endorsement',
            'test_methods': test['test_methods'],
            'runtime_limits': limits,
            'child_runtime_limits': {'tests': test['runtime_limits'],
                'primary': json.loads((fresh / 'measurements.json').read_text())['runtime_limits'],
                'audit': json.loads((audit_directory / 'measurements.json').read_text())['runtime_limits'],
                'lifting': json.loads((lifting_directory / 'measurements.json').read_text())['runtime_limits']},
            'test_report': test,
            'semantic_reference_equal': True,
            'retained_models_replayed': len(replay),
            'retained_lowerings_rechecked': len(lowerings),
            'replay': replay,
            'lowerings': lowerings,
            'primary_summary': observed['summary'],
            'separate_semantic_audit': {'semantic_reference_equal': True, 'unique_executable_descriptions': audit['unique_executable_descriptions'], **audit['totals']},
            'configuration_lifting_comparison': {'semantic_reference_equal': True, **lifting['summary']},
            'charged_operations_total': total,
            'charged_operations_by_campaign': campaign_operations,
            'aggregate_charged_operation_ceiling': 400000,
            'replay_charges': counts,
            'wall_seconds_descriptive': time.monotonic() - start,
            'scientific_limits': ['one clock', 'finite base-event/delivery/depth budgets', 'data-independent control', 'disjunctive facts', 'zero-time repair slots', 'well-nested interrupts', 'model-language lowering only']
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ('status','test_methods','semantic_reference_equal','retained_models_replayed','retained_lowerings_rechecked','charged_operations_total')}))

if __name__ == '__main__':
    main()
