#!/usr/bin/env python3
"""Budget-scaling benchmark. Timings are descriptive and never used for correctness."""
from __future__ import annotations
import importlib, inspect, json, os, statistics, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'; OUT.mkdir(exist_ok=True)
os.chdir(ROOT)
mm=importlib.import_module('icnc.model'); sm=importlib.import_module('icnc.semantics')
load=None
for n in ('load_model','read_model','parse_model_file'):
    if hasattr(mm,n): load=getattr(mm,n); break
if load is None: raise RuntimeError('no model loader found')
explore=None
for n in ('explore','analyze','reachable','search'):
    if hasattr(sm,n): explore=getattr(sm,n); break
if explore is None: raise RuntimeError('no exploration function found')

def call(fn,model,e,i):
    sig=inspect.signature(fn); kwargs={}
    positional=[]
    for idx,(name,p) in enumerate(sig.parameters.items()):
        if idx==0: positional.append(model); continue
        low=name.lower()
        if 'event' in low: kwargs[name]=e
        elif 'interrupt' in low or 'delivery' in low: kwargs[name]=i
        elif p.default is inspect.Parameter.empty:
            # Common positional convention after model.
            positional.append(e if len(positional)==1 else i)
    return fn(*positional,**kwargs)

def size_of(result):
    for name in ('states','reachable','seen','visited'):
        if hasattr(result,name):
            try:return len(getattr(result,name))
            except TypeError:pass
    if isinstance(result,dict): return len(result)
    if isinstance(result,(tuple,list)) and result:
        for x in result:
            if isinstance(x,(dict,set,list,tuple)): return len(x)
    return None
models=sorted((ROOT/'models').glob('*.json'))
assert len(models)==12
rows=[]
for path in models:
    model=load(path)
    for e in (4,8,12,16,24,32):
        for i in (0,1,2,4,8):
            times=[]; size=None
            for _ in range(3):
                t=time.perf_counter(); res=call(explore,model,e,i); times.append((time.perf_counter()-t)*1000)
                s=size_of(res); size=s if s is not None else size
            rows.append({'model':path.stem,'max_events':e,'max_interrupts':i,
                         'reachable_states':size,'median_ms':round(statistics.median(times),4),
                         'min_ms':round(min(times),4),'max_ms':round(max(times),4)})
assert len(rows)==12*6*5
summary={'status':'PASS','configurations':len(rows),'repetitions_per_configuration':3,
         'median_of_medians_ms':round(statistics.median(r['median_ms'] for r in rows),4),
         'maximum_median_ms':max(r['median_ms'] for r in rows),
         'maximum_reachable_states':max((r['reachable_states'] or 0) for r in rows),
         'timing_note':'Wall-clock timings are descriptive, environment-specific, and excluded from correctness claims.'}
(OUT/'scaling-rows.json').write_text(json.dumps(rows,indent=2,sort_keys=True))
(OUT/'scaling-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True))
print(json.dumps(summary))
