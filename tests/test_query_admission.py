"""Owned bounded arithmetic/metadata controls; no attack or deployment input."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import study
from icnc.examples import fixed
from icnc.frontier import build, plan_cost, synthesize, unsafe


class QueryAdmission(unittest.TestCase):
    def test_scientific_replay_distinguishes_float_from_integer_count(self):
        root = Path(__file__).resolve().parents[1]
        reference = json.loads((root / 'results/primary/reference.json').read_text(encoding='utf-8'))
        reference['summary']['total_model_instances'] = 84.0
        folder = Path(tempfile.mkdtemp(prefix='typed-reference-control-'))
        expected = folder / 'expected.json'
        expected.write_text(json.dumps(reference), encoding='utf-8')
        flags = ['-B', '-S']
        if sys.flags.optimize:
            flags.append('-' + 'O' * sys.flags.optimize)
        command = [sys.executable, *flags, str(root / 'study.py'), '--portable',
                   '--output', str(folder / 'observed'), '--compare', str(expected)]
        run = subprocess.run(command, cwd=root, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                             capture_output=True, timeout=45)
        (folder / 'command.json').write_text(json.dumps({'argv': command, 'exit_code': run.returncode,
             'stdout': run.stdout.decode('utf-8', errors='replace'),
             'stderr': run.stderr.decode('utf-8', errors='replace')}, indent=2), encoding='utf-8')
        self.assertNotEqual(run.returncode, 0, 'float metadata must not replay as an integer scientific count')
        actual = json.loads((folder / 'observed/reference.json').read_text(encoding='utf-8'))
        self.assertIs(type(actual['summary']['total_model_instances']), int)

    def test_boolean_plan_is_not_an_integer_query(self):
        frontier = build(fixed()[0])['frontier']
        with self.assertRaises(ValueError):
            unsafe(frontier, True, (1, 0, 0))

    def test_budget_boolean_and_float_are_not_integer_coordinates(self):
        frontier = build(fixed()[0])['frontier']
        for cap in ((True, 0, 0), (1.0, 0, 0)):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                unsafe(frontier, 0, cap)

    def test_empty_frontier_still_checks_budget_shape_and_sign(self):
        for cap in ((1, 0), (-1, 0, 0)):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                unsafe((), 0, cap)

    def test_synthesis_refuses_queries_above_construction_cap(self):
        m = fixed()[0].bounded((0, 0, 0))
        frontier = build(m)['frontier']
        self.assertEqual(frontier, ())
        with self.assertRaises(ValueError):
            synthesize(m, frontier, (1, 0, 0))

    def test_installation_cost_refuses_out_of_universe_plan(self):
        for plan in (True, -1, 2):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                plan_cost(fixed()[0], plan)

    def test_scan_counter_observation_rejected_even_under_optimization(self):
        actual_explore = study.explore
        def observation(m, plan, meter=None):
            answer = actual_explore(m, plan, meter)
            # Only an owned scientific counter-observation, not changed semantics.
            if m.name == 'F03-truncated-handler' and m.cap[1] == 0:
                answer = dict(answer, states=2)
            return answer
        # Preserve the complete owned counter-observation output on either mode;
        # the invoking test runner supplies a PID-private TEMP directory.
        folder = tempfile.mkdtemp(prefix='scan-counter-observation-')
        with patch.object(study, 'explore', side_effect=observation):
            with self.assertRaises(AssertionError):
                study.run(Path(folder))


if __name__ == '__main__':
    unittest.main()
