#!/usr/bin/env python3
"""Full existing-cohort query costs, one owned exact method per fresh process.

No hardware interrupt, side-channel, external target or defense deployment is
executed. All methods answer the same declared static-plan/sub-budget queries
and optimum sets. Certificate production/replay is an extra frontier output,
not a guarantee withheld from an exact ordinary semantic answer.
"""
import argparse
from contextlib import contextmanager
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import platform
import sys
import time
from icnc.checker import read, check
from icnc.config_lift import build as lift
from icnc.direct import explore
from icnc.frontier import build, synthesize, unsafe, Meter
from icnc.model import parse
from icnc.runtime_limits import configure_limits, check_cpu_limit, peak_rss_kib

ROOT = Path(__file__).resolve().parent


def own_memory():
    if sys.platform != 'win32':
        return {'peak_rss_kib': peak_rss_kib(), 'windows_peak_working_set_bytes': None}
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb',wintypes.DWORD), ('PageFaultCount',wintypes.DWORD)] + [
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    psapi = ctypes.WinDLL('psapi',use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
        raise OSError(ctypes.get_last_error(),'own-process memory query failed')
    return {'peak_rss_kib': None, 'windows_peak_working_set_bytes': counters.PeakWorkingSetSize,
            'windows_peak_commit_bytes': counters.PeakPagefileUsage,
            'scope': 'whole owned child peak observed before receipt write/exit; includes imports/input/answers, not an OS cap or Linux RSS'}


def ordinary_optimum(m,bits):
    safe = [p for p in range(1<<len(m.atoms)) if not bits & (1<<p)]
    costs = {p:sum(w for i,(_,w) in enumerate(m.atoms) if p & (1<<i)) for p in safe}
    best = min(costs.values()) if costs else None
    return {'minimum_cost':best,'optimal_plans':[p for p in safe if costs[p]==best],'safe_plans':len(safe)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('method',choices=('frontier','lifting','explicit'))
    ap.add_argument('--primary',type=Path,default=ROOT/'results/primary/reference.json')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--portable',action='store_true')
    args = ap.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT) or output.exists():
        raise ValueError('use a fresh owned output outside the retained artifact')
    limits = configure_limits(portable=args.portable)
    stages = {}
    @contextmanager
    def stage(name):
        cpu,wall = time.process_time(),time.perf_counter()
        yield
        cpu,wall = time.process_time()-cpu,time.perf_counter()-wall
        value = stages.setdefault(name,{'cpu_seconds':0.0,'wall_seconds':0.0})
        value['cpu_seconds'] += cpu
        value['wall_seconds'] += wall
    begin_cpu,begin_wall = time.process_time(),time.perf_counter()
    with stage('input_read_and_decode'):
        primary = read(args.primary)
        if len(primary['details'])!=84 or primary['summary']['total_model_instances']!=84:
            raise ValueError('requires the unchanged complete primary cohort')
    meter = Meter(limit=200000)
    rows = []
    plans = queries = optima = 0
    for name in sorted(primary['details']):
        with stage('model_admission'):
            m = parse(primary['details'][name]['model'])
        with stage('complete_construction'):
            if args.method=='frontier':
                object = build(m,meter)
            elif args.method=='lifting':
                object = lift(m,charge=meter.charge)
            else:
                object = [explore(m,p,meter) for p in range(1<<len(m.atoms))]
        if args.method=='frontier':
            with stage('full_certificate_replay'):
                check(m.raw(),object['certificate'],meter.charge)
        entries = []
        for cap in product(*(range(v+1) for v in m.cap)):
            with stage('all_plan_safety_queries'):
                if args.method=='lifting':
                    bits = object.truth_at(cap)
                else:
                    bits = 0
                    for p in range(1<<len(m.atoms)):
                        bad = unsafe(object['frontier'],p,cap,model=m) if args.method=='frontier' else any(
                            all(c<=b for c,b in zip(cost,cap)) for cost in object[p]['bad_costs'])
                        if bad: bits |= 1<<p
                queries += 1<<len(m.atoms)
            with stage('all_weighted_optimum_queries'):
                if args.method=='frontier':
                    optimum = synthesize(m,object['frontier'],cap)
                elif args.method=='lifting':
                    optimum = object.optimum(cap)
                else:
                    optimum = ordinary_optimum(m,bits)
                optima += 1
            entries.append({'cap':list(cap),'unsafe_plan_bits':bits,'optimum':optimum})
        rows.append({'model':name,'model_input':m.raw(),'queries':entries})
        plans += 1<<len(m.atoms)
    if queries!=5046 or optima!=526 or len(rows)!=84:
        raise AssertionError('complete primary query coverage changed')
    with stage('answer_encoding'):
        encoded = ''.join(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n' for row in rows).encode('utf-8')
    output.mkdir(parents=True,exist_ok=False)
    with stage('answer_write'):
        (output/'answers.jsonl').write_bytes(encoded)
    check_cpu_limit()
    through_cpu,through_wall = time.process_time()-begin_cpu,time.perf_counter()-begin_wall
    source_paths = [Path(__file__).resolve()] + [ROOT/name for name in
        ('icnc/__init__.py','icnc/model.py','icnc/checker.py','icnc/config_lift.py',
         'icnc/direct.py','icnc/frontier.py','icnc/runtime_limits.py')]
    with stage('receipt_source_binding'):
        sources = {p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in source_paths}
    memory = own_memory()
    receipt = {'method':args.method,'models':84,'plans':plans,'plan_budget_queries':queries,
               'optimal_plan_set_queries':optima,'stages':stages,'runtime_limits':limits,
               'cpu_seconds_through_answers':through_cpu,
               'wall_seconds_through_answers':through_wall,
               'memory':memory,'answer_sha256':sha256(encoded).hexdigest(),
               'primary_input_sha256':sha256(args.primary.read_bytes()).hexdigest(),
               'source_sha256':sources,'source_scope':'eight imported local modules; only the named arm executes its construction, not function coverage of every import',
               'environment':{'python':sys.version,'platform':platform.platform()},
               'contract':'all original static-plan/sub-budget safety and exact optimum/ties; identical models and weights',
               'scope':'one real owned CPython finite-model process per arm; not deployed interrupts or external SPLlift',
               'accounting':'stages include complete per-arm construction and frontier certificate consumer; startup/receipt I/O stay in external command wall',
               'comparison_note':'dense truth_at batches plan bits; explicit optimum reuses its just-computed bits; frontier/lifting optimum use their actual public APIs',
               'charged_operations':meter.counts}
    with (output/'receipt.json').open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(receipt,handle,indent=2)
        handle.write('\n')
    print(json.dumps({key:receipt[key] for key in ('method','models','plan_budget_queries','optimal_plan_set_queries',
                                                'cpu_seconds_through_answers','wall_seconds_through_answers','answer_sha256','memory')}))


if __name__=='__main__':
    main()
