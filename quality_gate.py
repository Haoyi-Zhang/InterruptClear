#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,sys
root=Path(__file__).resolve().parent
summary=json.loads((root/'results/summary.json').read_text())
assert summary['fixed_models']==12 and summary['fixed_safe']==6 and summary['fixed_unsafe']==6
assert summary['irreducibility_coordinates']==6
assert summary['exhaustive']['count']==1024
assert summary['random_id']['count']==250 and summary['random_holdout']['count']==250
assert summary['structural_ood']['count']==250
assert summary['metamorphic_comparisons']==300 and summary['metamorphic_failures']==0
assert summary['oracle_judgments']==1437 and summary['oracle_disagreements']==0
assert summary['certificate_mutations']==240 and summary['mutation_acceptances']==0
log=(root/'results/tests.log').read_text()
m=re.search(r'DISCOVERED_TESTS=(\d+)',log);assert m and int(m.group(1))>=55
models=list((root/'models').glob('*.json'));certs=list((root/'results/certificates').glob('*.json'))
assert len(models)==12 and len(certs)==12
manifest={}
for p in sorted([*models,*certs,*root.glob('*.py'),*root.glob('*.sh'),*root.glob('icnc/*.py'),*root.glob('tests/*.py')]):
    manifest[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
(root/'results/artifact-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
(root/'results/ALL_CODE_GATES_PASS').write_text('PASS\n')
print('ALL_CODE_GATES_PASS')
