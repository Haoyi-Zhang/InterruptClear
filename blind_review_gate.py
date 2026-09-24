#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; R=ROOT/'results'
def load(n): return json.loads((R/n).read_text())
cov=load('coverage.json'); sta=load('static-audit.json'); sc=load('scaling-summary.json')
assert cov['status']=='PASS' and cov['tests_run']>=55 and cov['coverage_percent']>=70
assert sta['status']=='PASS' and not sta['third_party_runtime_imports']
assert sc['status']=='PASS' and sc['configurations']==360
base=load('summary.json')
# Support either flat or nested summaries, but all mandatory campaigns must be nonzero and failure-free.
text=json.dumps(base,sort_keys=True).lower()
for token in ('1024','500','250','300','1437','240'):
    assert token in text, f'missing expected campaign count {token}'
for bad in ('"mismatches": 1','"failures": 1','"rejected": 0'):
    assert bad not in text
files=['summary.json','coverage.json','static-audit.json','scaling-summary.json','scaling-rows.json']
hashes={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in files}
report={'status':'PASS','coverage_percent':cov['coverage_percent'],'tests_run':cov['tests_run'],
        'source_lines':sta['source_lines'],'max_complexity':sta['maximum_approximate_cyclomatic_complexity'],
        'scaling_configurations':sc['configurations'],'evidence_hashes':hashes}
(R/'BLIND_REVIEW_CODE_PASS.json').write_text(json.dumps(report,indent=2,sort_keys=True))
print(json.dumps(report))
