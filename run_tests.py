"""Run and record the finite correctness, schema, and mutation checks."""
import unittest,sys,time,resource,json,argparse
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(2500*1024*1024,2500*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(170,180))
import verify
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('results/tests.json'));a=p.parse_args()
t=time.process_time();w=time.monotonic();suite=unittest.defaultTestLoader.discover('tests');res=unittest.TextTestRunner(verbosity=2).run(suite)
x=sys.modules['test_core']
r={'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'malformed_cases_rejected':x.MUTATIONS,'generator_obligations':x.GENERATOR_WORK,'oracle_constraint_systems':x.ORACLE_WORK,'verifier_obligations':verify.WORK_TOTAL,'cpu_seconds':time.process_time()-t,'wall_seconds':time.monotonic()-w,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));sys.exit(0 if res.wasSuccessful() else 1)
