#!/usr/bin/env python3
import sys,unittest
suite=unittest.defaultTestLoader.discover('tests')
r=unittest.TextTestRunner(verbosity=2).run(suite)
print(f'DISCOVERED_TESTS={r.testsRun}')
raise SystemExit(0 if r.wasSuccessful() else 1)
