from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable
import hashlib, json

_ALLOWED_EVENTS = {"nop", "arm", "use", "neutralize", "schedule", "clear_pending", "commit", "interrupt", "return"}
_ALLOWED_GUARDS = {"true", "<", "<=", "==", ">=", ">"}

class ModelError(ValueError):
    pass

@dataclass(frozen=True)
class Region:
    kind: str                 # point | open | above
    lo: int
    hi: int | None = None

    def label(self) -> str:
        if self.kind == "point": return f"={self.lo}"
        if self.kind == "open": return f"({self.lo},{self.hi})"
        return f"({self.lo},inf)"

    def representative(self) -> Fraction:
        if self.kind == "point": return Fraction(self.lo)
        if self.kind == "open": return Fraction(self.lo + int(self.hi), 2)
        return Fraction(self.lo + 1)

@dataclass(frozen=True)
class Transition:
    id: str
    src: str
    event: str
    dst: str | None = None
    guard_op: str = "true"
    guard_c: int = 0
    reset: bool = False
    target: str | None = None
    return_pc: str | None = None

@dataclass(frozen=True)
class Model:
    name: str
    locations: tuple[str, ...]
    initial_pc: str
    initial_taint: bool
    initial_pending: bool
    constants: tuple[int, ...]
    invariants: tuple[tuple[str, str, int], ...]
    urgent: frozenset[str]
    transitions: tuple[Transition, ...]
    max_events: int
    max_interrupts: int
    max_depth: int
    expected_safe: bool | None = None
    family: str = "unspecified"
    pair_coordinate: str | None = None

    def invariant(self, pc: str) -> tuple[str, int]:
        for loc, op, c in self.invariants:
            if loc == pc: return op, c
        return "true", 0

    def outgoing(self, pc: str) -> tuple[Transition, ...]:
        return tuple(t for t in self.transitions if t.src == pc)

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "locations": list(self.locations),
            "initial": {"pc": self.initial_pc, "taint": self.initial_taint, "pending": self.initial_pending},
            "constants": list(self.constants),
            "invariants": {loc: [op, c] for loc, op, c in self.invariants},
            "urgent": sorted(self.urgent),
            "transitions": [
                {"id": t.id, "src": t.src, "event": t.event, "dst": t.dst, "guard": [t.guard_op, t.guard_c],
                 "reset": t.reset, "target": t.target, "return": t.return_pc}
                for t in self.transitions
            ],
            "bounds": {"events": self.max_events, "interrupts": self.max_interrupts, "depth": self.max_depth},
            "expected_safe": self.expected_safe,
            "family": self.family,
            "pair_coordinate": self.pair_coordinate,
        }

    def digest(self) -> str:
        raw = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


def _expect_keys(obj: dict[str, Any], allowed: set[str], required: set[str], where: str) -> None:
    unknown = set(obj) - allowed
    missing = required - set(obj)
    if unknown or missing:
        raise ModelError(f"{where}: unknown={sorted(unknown)} missing={sorted(missing)}")


def _guard(raw: Any, where: str) -> tuple[str, int]:
    if raw is None: return "true", 0
    if not isinstance(raw, list) or len(raw) != 2 or raw[0] not in _ALLOWED_GUARDS or not isinstance(raw[1], int):
        raise ModelError(f"{where}: invalid guard")
    return str(raw[0]), int(raw[1])


def model_from_dict(d: dict[str, Any]) -> Model:
    _expect_keys(d, {"name","locations","initial","constants","invariants","urgent","transitions","bounds","expected_safe","family","pair_coordinate"},
                 {"name","locations","initial","constants","transitions","bounds"}, "model")
    name = d["name"]
    locations = tuple(d["locations"])
    if not isinstance(name, str) or not name or not locations or len(set(locations)) != len(locations):
        raise ModelError("invalid name or locations")
    initial = d["initial"]
    _expect_keys(initial, {"pc","taint","pending"}, {"pc","taint","pending"}, "initial")
    if initial["pc"] not in locations or not isinstance(initial["taint"], bool) or not isinstance(initial["pending"], bool):
        raise ModelError("invalid initial state")
    constants = sorted(set(d["constants"]) | {0})
    if not all(isinstance(x, int) and x >= 0 for x in constants): raise ModelError("constants must be nonnegative integers")
    invs = []
    for loc, raw in (d.get("invariants") or {}).items():
        if loc not in locations: raise ModelError("invariant for unknown location")
        op, c = _guard(raw, f"invariant {loc}")
        if c not in constants: raise ModelError("invariant constant missing from constants")
        invs.append((loc, op, c))
    urgent = frozenset(d.get("urgent") or [])
    if not urgent <= set(locations): raise ModelError("unknown urgent location")
    trs = []
    ids = set()
    for i, x in enumerate(d["transitions"]):
        _expect_keys(x, {"id","src","event","dst","guard","reset","target","return"}, {"id","src","event"}, f"transition[{i}]")
        if x["id"] in ids: raise ModelError("duplicate transition id")
        ids.add(x["id"])
        if x["src"] not in locations or x["event"] not in _ALLOWED_EVENTS: raise ModelError("bad transition source/event")
        op,c = _guard(x.get("guard"), f"transition[{i}]")
        if op != "true" and c not in constants: raise ModelError("guard constant missing from constants")
        event=x["event"]
        dst=x.get("dst")
        target=x.get("target")
        ret=x.get("return")
        if event == "interrupt":
            if target not in locations or ret not in locations or dst is not None: raise ModelError("interrupt needs target and return")
        elif event == "return":
            if any(v is not None for v in (dst,target,ret)): raise ModelError("return has no destination fields")
        else:
            if dst not in locations or target is not None or ret is not None: raise ModelError("ordinary transition needs dst only")
        trs.append(Transition(str(x["id"]), str(x["src"]), event, dst, op, c, bool(x.get("reset",False)), target, ret))
    b=d["bounds"]
    _expect_keys(b,{"events","interrupts","depth"},{"events","interrupts","depth"},"bounds")
    if not all(isinstance(b[k],int) and b[k] >= 0 for k in b): raise ModelError("invalid bounds")
    m=Model(name,locations,initial["pc"],initial["taint"],initial["pending"],tuple(constants),tuple(sorted(invs)),urgent,
            tuple(trs),b["events"],b["interrupts"],b["depth"],d.get("expected_safe"),d.get("family","unspecified"),d.get("pair_coordinate"))
    # all destinations must satisfy basic reachability shape, and return must occur only in a handler-capable model
    return m


def load_model(path: str | Path) -> Model:
    def no_dupes(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
        out={}
        for k,v in pairs:
            if k in out: raise ModelError(f"duplicate JSON key: {k}")
            out[k]=v
        return out
    with open(path,"r",encoding="utf-8") as f:
        return model_from_dict(json.load(f, object_pairs_hook=no_dupes))


def save_model(model: Model, path: str | Path) -> None:
    Path(path).write_text(json.dumps(model.canonical_dict(), indent=2, sort_keys=True)+"\n", encoding="utf-8")


def regions(model: Model) -> tuple[Region,...]:
    cs=model.constants
    out=[]
    for i,c in enumerate(cs):
        out.append(Region("point",c))
        if i+1 < len(cs): out.append(Region("open",c,cs[i+1]))
    out.append(Region("above",cs[-1]))
    return tuple(out)


def guard_holds(region: Region, op: str, c: int) -> bool:
    if op == "true": return True
    v=region.representative()
    return {"<":v<c,"<=":v<=c,"==":v==c,">=":v>=c,">":v>c}[op]


def invariant_holds(model: Model, pc: str, region: Region) -> bool:
    op,c=model.invariant(pc)
    return guard_holds(region,op,c)
