#!/usr/bin/env python3
"""Dependency-free statement-line coverage audit for the core ICNC package."""
from __future__ import annotations
import ast, json, os, sys, trace, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
os.chdir(ROOT)
# Run the complete discovered test suite under the stdlib tracer.
tr=trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.base_prefix])
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
runner=unittest.TextTestRunner(stream=open(OUT/'coverage-tests.log','w'), verbosity=1)
result=tr.runfunc(runner.run, suite)
if not result.wasSuccessful():
    raise SystemExit('tests failed under coverage tracing')
counts=tr.results().counts

STMT_TYPES=(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Expr,ast.Return,ast.Raise,
            ast.Assert,ast.Delete,ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,
            ast.If,ast.For,ast.AsyncFor,ast.While,ast.Try,ast.With,ast.AsyncWith,
            ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef,ast.Match,ast.Break,
            ast.Continue,ast.Pass)
files=[]; total=covered=0
for path in sorted((ROOT/'icnc').glob('*.py')):
    if path.name=='__init__.py':
        continue
    tree=ast.parse(path.read_text(), filename=str(path))
    executable=sorted({n.lineno for n in ast.walk(tree) if isinstance(n,STMT_TYPES) and hasattr(n,'lineno')})
    resolved=str(path.resolve())
    hit={line for (fn,line),count in counts.items() if Path(fn).resolve()==path.resolve() and count>0}
    cov=sorted(set(executable)&hit)
    miss=sorted(set(executable)-hit)
    pct=(100.0*len(cov)/len(executable)) if executable else 100.0
    files.append({'file':str(path.relative_to(ROOT)),'statement_lines':len(executable),
                  'covered_statement_lines':len(cov),'coverage_percent':round(pct,2),
                  'uncovered_lines':miss})
    total+=len(executable); covered+=len(cov)
overall=100.0*covered/total if total else 100.0
# This is deliberately labelled as AST statement-line coverage, not branch coverage.
report={'status':'PASS','method':'stdlib trace counts over AST statement lines',
        'tests_run':result.testsRun,'statement_lines':total,'covered_statement_lines':covered,
        'coverage_percent':round(overall,2),'threshold_percent':70.0,'files':files}
if overall < 70.0:
    report['status']='FAIL'
(OUT/'coverage.json').write_text(json.dumps(report,indent=2,sort_keys=True))
if report['status']!='PASS':
    raise SystemExit(f"statement-line coverage {overall:.2f}% < 70%")
print(json.dumps({k:report[k] for k in ('status','tests_run','coverage_percent')}))
