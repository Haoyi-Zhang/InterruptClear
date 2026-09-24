from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any
import hashlib, json
from .model import Model, load_model
from .contract import contract_reachability, Outcome, CallKey, compare_monolithic_and_contract
from .semantics import explore

class CertificateError(ValueError): pass

_TOP={"schema","model_sha256","model_name","verdict","monolithic","contract","comparison"}

def _state_row(s):
    return [s.pc,list(s.stack),s.region,s.taint,s.pending,s.bad,s.events,s.interrupts]

def _outcome_row(o: Outcome):
    return [o.bad_inside,o.taint,o.pending,o.region,o.events_used,o.interrupts_used]

def generate_certificate(model: Model) -> dict[str,Any]:
    mono=explore(model); cstates,_,summaries=contract_reachability(model); cmp=compare_monolithic_and_contract(model)
    rows=[]
    for k,outs in sorted(summaries.items(),key=lambda kv:repr(kv[0])):
        rows.append({"call":[k.transition_id,k.pc,list(k.stack),k.region,k.taint,k.pending,k.bad,k.events,k.interrupts],
                     "outcomes":[_outcome_row(o) for o in sorted(outs)]})
    return {
        "schema":"icnc-certificate-v1",
        "model_sha256":model.digest(),
        "model_name":model.name,
        "verdict":"safe" if not mono.unsafe else "unsafe",
        "monolithic":{"states":[_state_row(s) for s in sorted(mono.states)],
                        "edges":[[_state_row(e.src),e.label,_state_row(e.dst)] for e in sorted(mono.edges,key=repr)],
                        "bad_trace":[[lab,_state_row(s)] for lab,s in mono.shortest_bad_trace()]},
        "contract":{"states":[_state_row(s) for s in sorted(cstates)],"summaries":rows},
        "comparison":cmp,
    }

def strict_json_load(path: str | Path) -> dict:
    def hook(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise CertificateError(f"duplicate key {k}")
            d[k]=v
        return d
    with open(path,encoding="utf-8") as f: return json.load(f,object_pairs_hook=hook)

def verify_certificate(model: Model, cert: dict[str,Any]) -> tuple[bool,str]:
    if set(cert)!=_TOP: return False,f"top-level fields mismatch: {sorted(set(cert)^_TOP)}"
    if cert.get("schema")!="icnc-certificate-v1": return False,"wrong schema"
    expected=generate_certificate(model)
    # Exact canonical equality means every state, edge, result, trace and count is independently recomputed.
    a=json.dumps(cert,sort_keys=True,separators=(",",":"))
    b=json.dumps(expected,sort_keys=True,separators=(",",":"))
    if a!=b: return False,"certificate does not equal independently recomputed obligations"
    return True,"verified"

def save_certificate(model: Model,path: str | Path):
    Path(path).write_text(json.dumps(generate_certificate(model),indent=2,sort_keys=True)+"\n",encoding="utf-8")
