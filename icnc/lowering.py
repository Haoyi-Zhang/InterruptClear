"""Executable lowering of interruptible repair words to a phase-expanded model.

Base actions count against N. Repair/no-op slots do not. Acyclic phase progress
provides a derived finite microstep bound; all phases preserve the original
invariant and interrupt opportunities. This is a model-language correspondence,
not a processor/compiler refinement.
"""
from .model import parse

def expand(base, words):
    if type(words) is not dict:
        raise ValueError('repair word map')
    if any((q not in base.pcs for q in words)):
        raise ValueError('unknown installation location')
    if any((e.kind == 'repair' or e.t_clear is not None or e.p_clear is not None for e in base.edges)):
        raise ValueError('base must have no existing repair instrumentation')
    for word in words.values():
        if type(word) not in (list, tuple):
            raise ValueError('repair word')
        for slot in word:
            if type(slot) not in (list, tuple) or len(slot) != 2:
                raise ValueError('repair slot')
            atom, bit = slot
            if type(atom) is not str or atom not in base.atom_index or type(bit) is not str or bit not in ('t', 'p'):
                raise ValueError('repair word')
    phase = {q: [f'v{i}p{j}' for j in range(len(words.get(q, ())) + 1)] for i, q in enumerate(base.pcs)}
    projection = {p: q for q, ps in phase.items() for p in ps}
    edges = []
    origins = {}

    def emit(row, origin):
        row['id'] = f'x{len(edges)}'
        edges.append(row)
        origins[row['id']] = origin
    for q, ps in phase.items():
        for j, (atom, bit) in enumerate(words.get(q, ())):
            emit({'src': ps[j], 'dst': ps[j + 1], 'kind': 'repair', 'guard': [], 'reset': False, 'resume': None, 't_clear': atom if bit == 't' else None, 'p_clear': atom if bit == 'p' else None}, None)
        for e in base.outgoing[q]:
            starts = ps if e.kind == 'interrupt' else [ps[-1]]
            for src in starts:
                row = {'src': src, 'dst': None if e.dst is None else phase[e.dst][0], 'kind': e.kind, 'guard': [list(a) for a in e.guard], 'reset': e.reset, 'resume': None, 't_clear': None, 'p_clear': None}
                if e.kind == 'interrupt':
                    row['resume'] = src if e.resume == q else phase[e.resume][0]
                emit(row, e.id)
    raw = base.raw()
    # Names are provenance labels, not phase semantics. Do not make a valid
    # small input unlowerable just because its accepted name fills the limit.
    suffix = '-phased'
    raw['name'] = base.name + suffix if len(base.name) + len(suffix) <= 96 else base.name
    raw['locations'] = [p for q in base.pcs for p in phase[q]]
    raw['initial']['pc'] = phase[base.initial][0]
    raw['urgent'] = [p for q in base.urgent for p in phase[q]]
    raw['invariants'] = {p: [list(a) for a in g] for q, g in base.invariants for p in phase[q]}
    raw['edges'] = edges
    return (parse(raw), projection, origins)

def projection_obligations(base, expanded, projection, origins, words=None):
    """Local structural obligations sufficient for timed schedule equality.

    No source generator routine is trusted for the final checker: this helper
    gives a separately callable correspondence check, not independent authorship.
    """
    # The declared words are untrusted checker inputs. In particular an unknown
    # bit must not collapse both expected clear fields to None and masquerade as
    # a valid identity slot. Do not rely on expand having validated this input.
    if any(e.kind == 'repair' or e.t_clear is not None or e.p_clear is not None for e in base.edges):
        raise ValueError('base must have no existing repair instrumentation')
    if words is None:
        raise ValueError('declared repair words required')
    if words is not None:
        if type(words) is not dict or not set(words) <= set(base.pcs):
            raise ValueError('invalid declared repair words')
        for word in words.values():
            if type(word) not in (list, tuple):
                raise ValueError('invalid declared repair word')
            for slot in word:
                if type(slot) not in (list, tuple) or len(slot) != 2:
                    raise ValueError('invalid declared repair slot')
                atom, bit = slot
                if type(atom) is not str or atom not in base.atom_index or type(bit) is not str or bit not in ('t', 'p'):
                    raise ValueError('invalid declared repair slot')
    if type(projection) is not dict or type(origins) is not dict or set(origins) != {e.id for e in expanded.edges}:
        raise ValueError('invalid lowering annotation domain')
    base_edges = {e.id: e for e in base.edges}
    by_q = {q: [] for q in base.pcs}
    for p, q in projection.items():
        if type(p) is not str or type(q) is not str or q not in by_q:
            raise ValueError('invalid lowering projection')
        by_q[q].append(p)
    if not set(projection) == set(expanded.pcs):
        raise ValueError('lowering correspondence obligation failed')
    if not projection[expanded.initial] == base.initial:
        raise ValueError('lowering correspondence obligation failed')
    if not (expanded.taint == base.taint and expanded.pending == base.pending):
        raise ValueError('lowering correspondence obligation failed')
    if not (expanded.cap == base.cap and expanded.constants == base.constants):
        raise ValueError('lowering correspondence obligation failed')
    if not expanded.atoms == base.atoms:
        raise ValueError('lowering correspondence obligation failed')
    for p, q in projection.items():
        if not (p in expanded.urgent) == (q in base.urgent):
            raise ValueError('lowering correspondence obligation failed')
        if not expanded.inv.get(p, ()) == base.inv.get(q, ()):
            raise ValueError('lowering correspondence obligation failed')
    entries = {}
    ordered = {}
    for q, ps in by_q.items():
        repair = [e for e in expanded.edges if e.kind == 'repair' and e.src in ps]
        if not all((e.dst in ps and (not e.guard) and (not e.reset) for e in repair)):
            raise ValueError('lowering correspondence obligation failed')
        exits = [p for p in ps if not any((e.src == p for e in repair))]
        if not len(exits) == 1:
            raise ValueError('lowering correspondence obligation failed')
        starts = [p for p in ps if not any((e.dst == p for e in repair))]
        if not len(starts) == 1:
            raise ValueError('lowering correspondence obligation failed')
        entries[q] = starts[0]
        chain = []
        cur = starts[0]
        while cur != exits[0]:
            step = [e for e in repair if e.src == cur]
            if not len(step) == 1:
                raise ValueError('lowering correspondence obligation failed')
            chain.append(step[0])
            cur = step[0].dst
        ordered[q] = chain
        if words is not None:
            if not len(chain) == len(words.get(q, ())):
                raise ValueError('lowering correspondence obligation failed')
            for e, (a, bit) in zip(chain, words.get(q, ())):
                if not (e.t_clear == (a if bit == 't' else None) and e.p_clear == (a if bit == 'p' else None)):
                    raise ValueError('lowering correspondence obligation failed')
        for p in ps:
            visited = set()
            cur = p
            while cur != exits[0]:
                if not cur not in visited:
                    raise ValueError('lowering correspondence obligation failed')
                visited.add(cur)
                outgoing = [e for e in repair if e.src == cur]
                if not len(outgoing) == 1:
                    raise ValueError('lowering correspondence obligation failed')
                cur = outgoing[0].dst
        for p in ps:
            here = [e for e in expanded.outgoing[p] if e.kind != 'repair']
            expected = [e for e in base.outgoing[q] if e.kind == 'interrupt' or p == exits[0]]
            if not sorted((origins[e.id] for e in here)) == sorted((e.id for e in expected)):
                raise ValueError('lowering correspondence obligation failed')
    if not expanded.initial == entries[base.initial]:
        raise ValueError('lowering correspondence obligation failed')
    for e in expanded.edges:
        if e.kind == 'repair':
            if not origins[e.id] is None:
                raise ValueError('lowering correspondence obligation failed')
            continue
        b = base_edges[origins[e.id]]
        if not (projection[e.src] == b.src and e.kind == b.kind and (e.guard == b.guard) and (e.reset == b.reset)):
            raise ValueError('lowering correspondence obligation failed')
        if not (None if e.dst is None else projection[e.dst]) == b.dst:
            raise ValueError('lowering correspondence obligation failed')
        if not (None if e.resume is None else projection[e.resume]) == b.resume:
            raise ValueError('lowering correspondence obligation failed')
        if not (e.t_clear is None and e.p_clear is None):
            raise ValueError('lowering correspondence obligation failed')
        if b.dst is not None:
            if not e.dst == entries[b.dst]:
                raise ValueError('lowering correspondence obligation failed')
        if b.kind == 'interrupt':
            if not e.resume == (e.src if b.resume == b.src else entries[b.resume]):
                raise ValueError('lowering correspondence obligation failed')
    return True
