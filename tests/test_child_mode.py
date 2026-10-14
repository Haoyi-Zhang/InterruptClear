"""Inspect the owned first-child invocation without running an unreviewed child."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import verify_all


class ChildMode(unittest.TestCase):
    def test_full_reproduction_propagates_interpreter_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            argv = ['verify_all.py', '--portable', '--keep-work', '--scratch', str(folder),
                    '--output', str(folder / 'report.json')]
            with patch.object(sys, 'argv', argv), \
                    patch.object(verify_all.subprocess, 'run', side_effect=RuntimeError('owned stop before child')) as launch:
                with self.assertRaisesRegex(RuntimeError, 'owned stop before child'):
                    verify_all.main()
            command = launch.call_args.args[0]
            required = {'-B'}
            if sys.flags.no_site:
                required.add('-S')
            if sys.flags.optimize:
                required.add('-' + 'O' * sys.flags.optimize)
            self.assertFalse(required - set(command), ('missing interpreter flags', required - set(command), command))
