from __future__ import annotations
from copy import deepcopy
import random
from .model import model_from_dict, Model

def tr(i,src,event,dst=None,guard=None,reset=False,target=None,ret=None):
    d={"id":f"t{i}","src":src,"event":event}
    if dst is not None:d["dst"]=dst
    if guard is not None:d["guard"]=guard
    if reset:d["reset"]=True
    if target is not None:d["target"]=target
    if ret is not None:d["return"]=ret
    return d

def _base(name,locs,trans,initial_taint=False,initial_pending=False,events=12,interrupts=2,depth=2,
          constants=(0,1),invariants=None,urgent=None,expected=None,family="separation",coord=None):
    return model_from_dict({
        "name":name,"locations":locs,
        "initial":{"pc":"c0","taint":bool(initial_taint),"pending":bool(initial_pending)},
        "constants":list(constants),"invariants":invariants or {},"urgent":urgent if urgent is not None else list(locs),
        "transitions":trans,"bounds":{"events":events,"interrupts":interrupts,"depth":depth},
        "expected_safe":expected,"family":family,"pair_coordinate":coord,
    })

def separation_models()->list[Model]:
    out=[]
    # 1. internal bad-prefix coordinate
    loc=["c0","c1","done","h0","h1","h2","hr"]
    common=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(1,"h0","arm","h1"),
            tr(3,"h2","neutralize","hr"),tr(4,"hr","return"),tr(5,"c1","nop","done")]
    out.append(_base("P1-safe-no-internal-use",loc,common+[tr(2,"h1","nop","h2")],expected=True,coord="bad_inside"))
    out.append(_base("P1-unsafe-internal-use",loc,common+[tr(2,"h1","use","h2")],expected=False,coord="bad_inside"))
    # 2. residual taint coordinate
    loc=["c0","c1","done","h0","h1","hr"]
    common=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(2,"h1","nop","hr"),tr(3,"hr","return"),tr(4,"c1","use","done")]
    out.append(_base("P2-safe-cleared-taint",loc,common+[tr(1,"h0","neutralize","h1")],initial_taint=True,expected=True,coord="taint"))
    out.append(_base("P2-unsafe-residual-taint",loc,common+[tr(1,"h0","nop","h1")],initial_taint=True,expected=False,coord="taint"))
    # 3. pending coordinate
    loc=["c0","c1","c2","done","h0","h1","hr"]
    common=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(2,"h1","nop","hr"),tr(3,"hr","return"),
            tr(4,"c1","commit","c2"),tr(5,"c2","use","done")]
    out.append(_base("P3-safe-cleared-pending",loc,common+[tr(1,"h0","clear_pending","h1")],initial_pending=True,expected=True,coord="pending"))
    out.append(_base("P3-unsafe-pending-commit",loc,common+[tr(1,"h0","nop","h1")],initial_pending=True,expected=False,coord="pending"))
    # 4. return region coordinate; caller is urgent, so it observes the boundary region before any delay.
    loc=["c0","c1","done","h0"]
    caller=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(2,"c1","neutralize","done",guard=["==",0]),
            tr(3,"c1","use","done",guard=["==",1])]
    out.append(_base("P4-safe-return-at-zero",loc,caller+[tr(1,"h0","return",guard=["==",0])],initial_taint=True,
                     invariants={"h0":["<=",0]},urgent=loc,expected=True,coord="region"))
    out.append(_base("P4-unsafe-return-at-one",loc,caller+[tr(1,"h0","return",guard=["==",1])],initial_taint=True,
                     invariants={"h0":["<=",1]},urgent=["c0","c1","done"],expected=False,coord="region"))
    # 5. event-cost coordinate
    highloc=["c0","c1","c2","done","h0","h1","h2","h3"]
    high=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(1,"h0","nop","h1"),tr(2,"h1","nop","h2"),
          tr(3,"h2","nop","h3"),tr(4,"h3","return"),tr(5,"c1","arm","c2"),tr(6,"c2","use","done")]
    out.append(_base("P5-safe-event-budget-consumed",highloc,high,events=6,expected=True,coord="events_used"))
    lowloc=["c0","c1","c2","done","h0","h1","h2"]
    low=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(1,"h0","nop","h1"),tr(2,"h1","nop","h2"),
         tr(3,"h2","return"),tr(4,"c1","arm","c2"),tr(5,"c2","use","done")]
    out.append(_base("P5-unsafe-event-budget-remains",lowloc,low,events=6,expected=False,coord="events_used"))
    # 6. interrupt-cost coordinate; equal event cost in the summarized initial episode.
    highloc=["c0","c1","c2","done","h0","h1","n0","nr","d0","dr"]
    high=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(1,"h0","interrupt",target="n0",ret="h1"),
          tr(2,"n0","nop","nr"),tr(3,"nr","return"),tr(4,"h1","return"),
          tr(5,"c1","interrupt",target="d0",ret="c2"),tr(6,"d0","arm","dr"),tr(7,"dr","return"),tr(8,"c2","use","done")]
    out.append(_base("P6-safe-interrupt-budget-consumed",highloc,high,events=12,interrupts=2,depth=2,expected=True,coord="interrupts_used"))
    lowloc=["c0","c1","c2","done","h0","ha","hb","h1","d0","dr"]
    low=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(1,"h0","nop","ha"),tr(2,"ha","nop","hb"),
         tr(3,"hb","nop","h1"),tr(4,"h1","return"),tr(5,"c1","interrupt",target="d0",ret="c2"),
         tr(6,"d0","arm","dr"),tr(7,"dr","return"),tr(8,"c2","use","done")]
    out.append(_base("P6-unsafe-interrupt-budget-remains",lowloc,low,events=12,interrupts=2,depth=2,expected=False,coord="interrupts_used"))
    return sorted(out,key=lambda m:m.name)

def generated_model(index:int,family:str="exhaustive")->Model:
    # Ten independent syntax bits create 1,024 small but semantically diverse models.
    bits=[(index>>i)&1 for i in range(10)]
    actions=["nop","neutralize","clear_pending","schedule","arm","commit"]
    a1=actions[(bits[2]+2*bits[3])%len(actions)]
    a2=actions[(bits[4]+2*bits[5])%len(actions)]
    caller1="commit" if bits[6] else "nop"
    caller2="use" if bits[7] else "neutralize"
    nested=bool(bits[9])
    loc=["c0","c1","c2","done","h0","h1","hr"]
    ts=[tr(0,"c0","interrupt",target="h0",ret="c1"),tr(1,"h0",a1,"h1"),tr(2,"h1",a2,"hr")]
    if nested:
        loc += ["n0","nr"]
        ts += [tr(3,"hr","interrupt",target="n0",ret="hr2"),tr(4,"n0","nop","nr"),tr(5,"nr","return")]
        loc += ["hr2"]; ts += [tr(6,"hr2","return")]; k=7
    else:
        ts += [tr(3,"hr","return")]; k=4
    ts += [tr(k,"c1",caller1,"c2"),tr(k+1,"c2",caller2,"done")]
    return _base(f"{family}-{index:04d}",loc,ts,initial_taint=bool(bits[0]),initial_pending=bool(bits[1]),
                 events=12,interrupts=2,depth=2,expected=None,family=family)

def random_model(seed:int,family:str="random-id")->Model:
    r=random.Random(seed)
    n=r.randint(1,5)
    actions=[r.choice(["nop","arm","neutralize","schedule","clear_pending","commit","use"]) for _ in range(n)]
    loc=["c0","c1","c2","done"]+[f"h{i}" for i in range(n+1)]
    ts=[tr(0,"c0","interrupt",target="h0",ret="c1")]
    for i,a in enumerate(actions):ts.append(tr(i+1,f"h{i}",a,f"h{i+1}"))
    ts.append(tr(n+1,f"h{n}","return"));ts.append(tr(n+2,"c1",r.choice(["nop","commit","arm","neutralize"]),"c2"));ts.append(tr(n+3,"c2",r.choice(["use","nop","neutralize"]),"done"))
    return _base(f"{family}-{seed:04d}",loc,ts,initial_taint=r.choice([False,True]),initial_pending=r.choice([False,True]),
                 events=n+6,interrupts=2,depth=2,family=family)

def ood_model(seed:int)->Model:
    # Structural holdout: two nested calls, a larger clock alphabet, nonzero guards, and mixed urgency.
    r=random.Random(100000+seed)
    loc=["c0","c1","done","h0","h1","h2","n0","n1","nr","hret"]
    ts=[tr(0,"c0","interrupt",target="h0",ret="c1"),
        tr(1,"h0",r.choice(["arm","schedule","nop"]),"h1",reset=True),
        tr(2,"h1","interrupt",target="n0",ret="h2",guard=[">=",1]),
        tr(3,"n0",r.choice(["neutralize","clear_pending","nop"]),"n1"),
        tr(4,"n1",r.choice(["commit","nop","neutralize"]),"nr",guard=["<",3]),
        tr(5,"nr","return"),tr(6,"h2",r.choice(["neutralize","nop","commit"]),"hret"),tr(7,"hret","return"),
        tr(8,"c1",r.choice(["use","commit","neutralize","nop"]),"done")]
    # h1 must permit time to reach one; all other locations are urgent.
    urgent=[x for x in loc if x!="h1"]
    return _base(f"ood-{seed:04d}",loc,ts,initial_taint=r.choice([False,True]),initial_pending=r.choice([False,True]),
                 events=14,interrupts=3,depth=3,constants=(0,1,2,3),invariants={"h1":["<=",2]},urgent=urgent,family="structural-ood")

def rename_model(m:Model)->Model:
    d=m.canonical_dict(); mp={x:f"q{i:03d}" for i,x in enumerate(reversed(d["locations"]))}
    d["name"] += "-renamed"; d["locations"]=[mp[x] for x in d["locations"]]; d["initial"]["pc"]=mp[d["initial"]["pc"]]
    d["invariants"]={mp[k]:v for k,v in d["invariants"].items()}; d["urgent"]=[mp[x] for x in d["urgent"]]
    for t in d["transitions"]:
        t["src"]=mp[t["src"]]
        if t.get("dst") is not None:t["dst"]=mp[t["dst"]]
        if t.get("target") is not None:t["target"]=mp[t["target"]]
        if t.get("return") is not None:t["return"]=mp[t["return"]]
    return model_from_dict(d)

def permute_model(m:Model)->Model:
    d=m.canonical_dict();d["name"]+="-permuted";d["transitions"]=list(reversed(d["transitions"]));return model_from_dict(d)

def unreachable_extension(m:Model)->Model:
    d=m.canonical_dict();d["name"]+="-unreachable";d["locations"].append("unreachable_sink");d["urgent"].append("unreachable_sink")
    d["transitions"].append({"id":"unreachable-loop","src":"unreachable_sink","event":"arm","dst":"unreachable_sink","guard":["true",0],"reset":False,"target":None,"return":None})
    return model_from_dict(d)
