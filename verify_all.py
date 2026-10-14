#!/usr/bin/env python3
"""Clean semantic reproduction and replay; status is emitted only after checks."""
from pathlib import Path
from contextlib import contextmanager
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from icnc.checker import check, read
from icnc.lowering import projection_obligations
from icnc.model import parse, scientific_equal
from icnc.runtime_limits import configure_limits,check_cpu_limit
from run_tests import EXPECTED_TEST_METHODS

ROOT = Path(__file__).resolve().parent

def python_command(script, *arguments):
    """Children inherit the reviewed parent's optimization/site contract."""
    flags = ['-B']
    if sys.flags.optimize:
        flags.append('-' + 'O' * sys.flags.optimize)
    if sys.flags.no_site:
        flags.append('-S')
    return [sys.executable, *flags, str(script), *map(str, arguments)]

@contextmanager
def reproduction_workspace(scratch, keep_work=False):
    """Keep raw campaign files on either outcome when explicitly requested."""
    if keep_work:
        directory = Path(tempfile.mkdtemp(prefix='neutralization-reproduction-', dir=scratch))
        print('Raw reproduction workspace: ' + str(directory.resolve()), flush=True)
        yield directory
    else:
        with tempfile.TemporaryDirectory(prefix='neutralization-reproduction-', dir=scratch) as temp:
            yield Path(temp)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT / 'results' / 'verification.json')
    ap.add_argument('--portable', action='store_true')
    ap.add_argument('--scratch', type=Path, default=ROOT / 'results' / 'scratch')
    ap.add_argument('--keep-work', action='store_true', help='retain raw child campaign files after success or failure')
    args = ap.parse_args()
    limits = configure_limits(portable=args.portable)
    start = time.monotonic()
    env = dict(os.environ, PYTHONHASHSEED='0')
    args.scratch.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(args.scratch.resolve()), TMP=str(args.scratch.resolve()),
               TMPDIR=str(args.scratch.resolve()), PYTHONDONTWRITEBYTECODE='1')
    portable = ['--portable'] if args.portable else []
    counts = {}
    def charge(kind, amount=1):
        check_cpu_limit()
        counts[kind] = counts.get(kind, 0) + amount
        if sum(counts.values()) > 100000:
            raise RuntimeError('verification work ceiling; no verdict')
    with reproduction_workspace(args.scratch, args.keep_work) as temp:
        child_commands = []
        def run_child(script, arguments, timeout):
            argv = python_command(ROOT / script, *arguments)
            begin = time.monotonic()
            result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
            row = {'argv': argv, 'exit_code': result.returncode,
                   'wall_seconds': time.monotonic() - begin,
                   'stdout': result.stdout.decode('utf-8', errors='replace'),
                   'stderr': result.stderr.decode('utf-8', errors='replace')}
            child_commands.append(row)
            (temp / ('command-' + Path(script).stem + '.json')).write_text(
                json.dumps(row, indent=2) + '\n', encoding='utf-8', newline='\n')
            if result.returncode:
                raise RuntimeError('child failed; raw command output retained: ' + script)
        testfile = temp / 'tests.json'
        run_child('run_tests.py', ['--output', testfile, *portable], 190)
        test = json.loads(testfile.read_text())
        if test['test_methods'] != EXPECTED_TEST_METHODS or not test['successful'] or test['failures'] or test['errors'] or test['skips']:
            raise RuntimeError('test result mismatch')
        fresh = temp / 'study'
        run_child('study.py', ['--output', fresh, '--compare', ROOT / 'results' / 'primary' / 'reference.json', *portable], 190)
        original = ROOT / 'results' / 'primary'
        observed = json.loads((fresh / 'reference.json').read_text())
        audit_directory = temp / 'semantic-audit'
        run_child('audit_semantics.py', ['--out', audit_directory, '--compare', ROOT / 'results' / 'audit' / 'reference.json', *portable], 40)
        audit = json.loads((audit_directory / 'reference.json').read_text())
        lifting_directory = temp / 'configuration-lifting'
        run_child('compare_lifting.py', ['--primary', fresh / 'reference.json', '--output', lifting_directory,
                                      '--compare', ROOT / 'results' / 'lifting' / 'reference.json', *portable], 190)
        lifting = json.loads((lifting_directory / 'reference.json').read_text())
        # Exact retained model/certificate bytes are not cryptographic evidence;
        # compare parsed scientific values instead of generating hash manifests.
        for folder in ('models', 'certificates', 'lowerings'):
            a = {p.name for p in (original / folder).glob('*.json')}
            b = {p.name for p in (fresh / folder).glob('*.json')}
            if a != b:
                raise RuntimeError('retained file set differs: ' + folder)
            for name in a:
                if not scientific_equal(json.loads((original / folder / name).read_text()), json.loads((fresh / folder / name).read_text())):
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
            'raw_workspace': str(temp.resolve()) if args.keep_work else None,
            'runtime_limits': limits,
            'child_runtime_limits': {'tests': test['runtime_limits'],
                'primary': json.loads((fresh / 'measurements.json').read_text())['runtime_limits'],
                'audit': json.loads((audit_directory / 'measurements.json').read_text())['runtime_limits'],
                'lifting': json.loads((lifting_directory / 'measurements.json').read_text())['runtime_limits']},
            'test_report': test,
            'child_commands': child_commands,
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
