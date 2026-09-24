#!/usr/bin/env python3
from __future__ import annotations
import ast, json, py_compile, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
stdlib=set(__import__('sys').stdlib_module_names)
rows=[]; imports=set(); max_complexity=0; max_function=''
for path in sorted(list((ROOT/'icnc').glob('*.py'))+list(ROOT.glob('*.py'))+list((ROOT/'tests').glob('*.py'))):
    py_compile.compile(str(path),doraise=True)
    text=path.read_text()
    tree=ast.parse(text,filename=str(path))
    assert not re.search(r'\b(?:TODO|FIXME|XXX)\b',text,re.I), f'unresolved marker in {path}'
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            decisions=sum(isinstance(x,(ast.If,ast.For,ast.AsyncFor,ast.While,ast.Try,ast.IfExp,ast.BoolOp,ast.Match,ast.comprehension)) for x in ast.walk(node))
            complexity=1+decisions
            if complexity>max_complexity:
                max_complexity=complexity; max_function=f'{path.name}:{node.name}'
    rows.append({'file':str(path.relative_to(ROOT)),'lines':len(text.splitlines())})
third=sorted(x for x in imports if x not in stdlib and x not in {'icnc','tests','__future__'})
report={'status':'PASS','python_files':len(rows),'source_lines':sum(x['lines'] for x in rows),
        'maximum_approximate_cyclomatic_complexity':max_complexity,'maximum_function':max_function,
        'third_party_runtime_imports':third,'files':rows,
        'notes':'Complexity is 1 plus AST decision nodes; runtime core is required to remain standard-library only.'}
if third or max_complexity>35:
    report['status']='FAIL'
(OUT/'static-audit.json').write_text(json.dumps(report,indent=2,sort_keys=True))
if report['status']!='PASS': raise SystemExit(json.dumps(report))
print(json.dumps({k:report[k] for k in ('status','python_files','source_lines','maximum_approximate_cyclomatic_complexity','third_party_runtime_imports')}))
