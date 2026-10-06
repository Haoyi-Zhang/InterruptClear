"""Regression for preserving the finite campaign's raw evidence on failure."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import audit_semantics
from verify_all import reproduction_workspace


class RawEvidence(unittest.TestCase):
    def test_keep_work_survives_success_and_failure(self):
        # The outer directory owns only this test's tiny synthetic files.
        with tempfile.TemporaryDirectory() as scratch:
            for fail in (False, True):
                workspace = None
                try:
                    with reproduction_workspace(Path(scratch), keep_work=True) as workspace:
                        (workspace / 'observed.json').write_text('{"finite_cases": 1}\n', encoding='utf-8')
                        if fail:
                            raise RuntimeError('synthetic comparison failure')
                except RuntimeError as error:
                    self.assertTrue(fail)
                    self.assertEqual(str(error), 'synthetic comparison failure')
                self.assertIsNotNone(workspace)
                self.assertEqual((workspace / 'observed.json').read_text(encoding='utf-8'),
                                 '{"finite_cases": 1}\n')

    def test_audit_comparison_failure_retains_observation(self):
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            reference = scratch / 'expected.json'
            reference.write_text('{"finite_cases": 2}\n', encoding='utf-8')
            observed = {'finite_cases': 1}
            output = scratch / 'observed'
            with patch.object(sys, 'argv', ['audit_semantics.py', '--out', str(output),
                                            '--compare', str(reference), '--portable']), \
                    patch.object(audit_semantics, 'run', return_value=observed), \
                    patch.object(audit_semantics, 'configure_limits', return_value={}), \
                    patch.object(audit_semantics, 'check_cpu_limit'):
                with self.assertRaisesRegex(AssertionError, 'retained exploratory audit differs'):
                    audit_semantics.main()
            self.assertEqual(json.loads((output / 'reference.json').read_text(encoding='utf-8')), observed)
            self.assertEqual(json.loads((output / 'measurements.json').read_text(encoding='utf-8'))
                             ['deterministic_reference_sha256'], audit_semantics.digest(observed))
