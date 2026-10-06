#!/usr/bin/env python3
"""Run the finite model suite; report the actual host limit capabilities."""
import argparse,json,time,unittest,sys
from collections import Counter
from pathlib import Path
from icnc.runtime_limits import configure_limits,check_cpu_limit,peak_rss_kib
ROOT=Path(__file__).resolve().parent
EXPECTED_TEST_METHODS=66

class BoundedResult(unittest.TextTestResult):
 def startTest(self,test):
  check_cpu_limit();super().startTest(test)
 def stopTest(self,test):
  super().stopTest(test);check_cpu_limit()

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results'/'tests.json');ap.add_argument('--portable',action='store_true');args=ap.parse_args()
 limits=configure_limits(portable=args.portable)
 start=time.process_time();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'));r=unittest.TextTestRunner(verbosity=2,resultclass=BoundedResult).run(suite)
 module_counts={}
 if 'test_core' in sys.modules:module_counts['test_core']=dict(sys.modules['test_core'].METER.counts)
 if 'test_config_lift' in sys.modules:module_counts['test_config_lift']=dict(sys.modules['test_config_lift'].COUNTS)
 combined=Counter()
 for counts in module_counts.values():combined.update(counts)
 successful=r.wasSuccessful() and not r.skipped and r.testsRun==EXPECTED_TEST_METHODS
 data={'test_methods':r.testsRun,'expected_test_methods':EXPECTED_TEST_METHODS,'failures':len(r.failures),'errors':len(r.errors),'skips':len(r.skipped),'successful':successful,'measured_cpu_seconds':time.process_time()-start,'peak_rss_kib':peak_rss_kib(),'runtime_limits':limits,'charged_operations':dict(combined),'charged_operations_by_module':module_counts,'mutation_cases_in_systematic_test':20}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(data,indent=2));sys.exit(0 if successful else 1)
