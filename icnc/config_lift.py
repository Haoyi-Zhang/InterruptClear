"""Exact Boolean configuration lifting on the declared bounded skeleton.

Bit x of a fact vector means that some execution under static plan x reaches
the skeleton state with that fact true.  This module does not use causal masks
or frontier construction.  It shares the input loader and successor relation;
it is a representation comparator, not an independent timing specification.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from .model import Model, initial_state, successors, _prepare, _successors


class LiftLimitExceeded(RuntimeError):
    """Resource ceiling exceeded; no exact result is returned."""


class Counter:
    def __init__(self, limit=250000, charge=None):
        if type(limit) is not int or limit < 0:
            raise ValueError('nonnegative integer operation limit required')
        self.limit = limit
        self.counts = {}
        self.external_charge = charge

    def add(self, kind, amount=1):
        self.counts[kind] = self.counts.get(kind, 0) + amount
        if sum(self.counts.values()) > self.limit:
            raise LiftLimitExceeded('configuration-lifting operation ceiling; no verdict')
        if self.external_charge is not None:
            self.external_charge(kind, amount)


@dataclass
class Lifted:
    model: Model
    values: dict
    bad_by_cost: dict
    edges: int
    plans: int
    full: int
    disabled: tuple
    counter: Counter

    def checked_cap(self, cap):
        if not isinstance(cap, (tuple, list)) or len(cap) != 3:
            raise ValueError('three smaller-budget coordinates required')
        if any(type(v) is not int or not 0 <= v <= hi for v, hi in zip(cap, self.model.cap)):
            raise ValueError('query cap must be componentwise within construction cap')
        return tuple(cap)

    def truth_at(self, cap):
        """Return all unsafe plan bits at a smaller cap, without re-exploring."""
        cap = self.checked_cap(cap)
        bits = 0
        for cost, value in self.bad_by_cost.items():
            self.counter.add('query_cost_bucket_tests')
            if all(c <= b for c, b in zip(cost, cap)):
                self.counter.add('query_bitwise_or')
                bits |= value
        return bits

    def unsafe(self, plan, cap):
        if type(plan) is not int or not 0 <= plan < self.plans:
            raise ValueError('static plan outside configured domain')
        bits = self.truth_at(cap)
        self.counter.add('query_plan_bit_tests')
        return bool(bits & (1 << plan))

    def optimum(self, cap):
        bits = self.truth_at(cap)
        best = None
        winners = []
        safe = 0
        for plan in range(self.plans):
            self.counter.add('optimization_plan_bit_tests')
            if bits & (1 << plan):
                continue
            safe += 1
            cost = 0
            for i, (_, weight) in enumerate(self.model.atoms):
                self.counter.add('optimization_atom_tests')
                if plan & (1 << i):
                    cost += weight
            if best is None or cost < best:
                best, winners = cost, [plan]
            elif cost == best:
                winners.append(plan)
        return {'minimum_cost': best, 'optimal_plans': winners, 'safe_plans': safe}


def build(m: Model, charge=None, operation_limit=250000, state_limit=250000):
    """Lift all plans through constants, optional clears, copying and OR.

    Delays preserve both vectors.  Uses contribute the pre-action taint vector
    after selected pre-edge clears, including a use before any matching return.
    """
    if type(state_limit) is not int or state_limit < 1:
        raise ValueError('positive integer state limit required')
    counter = Counter(operation_limit, charge)
    plans = 1 << len(m.atoms)
    full = (1 << plans) - 1
    disabled = []
    for atom in range(len(m.atoms)):
        bits = 0
        for plan in range(plans):
            counter.add('configuration_literal_bit_tests')
            if not plan & (1 << atom):
                bits |= 1 << plan
        disabled.append(bits)

    root = initial_state(m)
    structure = _prepare(m)
    seen = {root}
    todo = deque([root])
    graph = {}
    while todo:
        state = todo.popleft()
        arcs = tuple(_successors(m, state, structure))
        graph[state] = arcs
        counter.add('skeleton_successor_arcs', len(arcs))
        for _, dest, _ in arcs:
            if dest not in seen:
                seen.add(dest)
                if len(seen) > state_limit:
                    raise LiftLimitExceeded('configuration-lifting state ceiling; no verdict')
                todo.append(dest)

    # Same exact region skeleton as the other methods, independently traversed.
    rank = m.zero_rank
    order = sorted(seen, key=lambda s: (s[0], rank[s[3]], s[4], s[1], s[2], s[3], s[5]))
    values = {state: (0, 0) for state in seen}
    values[root] = (full if m.taint else 0, full if m.pending else 0)
    bad_by_cost = {}
    index = m.atom_index if structure is None else structure.atom_index
    for state in order:
        taint, pending = values[state]
        for _, dest, edge in graph[state]:
            counter.add('fact_transfer_arcs')
            nt, np = taint, pending
            if edge is not None:
                if edge.t_clear is not None:
                    counter.add('clear_bitwise_and')
                    nt &= disabled[index[edge.t_clear]]
                if edge.p_clear is not None:
                    counter.add('clear_bitwise_and')
                    np &= disabled[index[edge.p_clear]]
                if edge.kind == 'use' and nt:
                    counter.add('bad_bucket_bitwise_or')
                    cost = dest[:3]
                    bad_by_cost[cost] = bad_by_cost.get(cost, 0) | nt
                if edge.kind == 'arm':
                    nt = full
                    counter.add('constant_fact_assignments')
                elif edge.kind == 'neutralize':
                    nt = 0
                    counter.add('constant_fact_assignments')
                elif edge.kind == 'schedule':
                    np = full
                    counter.add('constant_fact_assignments')
                elif edge.kind == 'clear_pending':
                    np = 0
                    counter.add('constant_fact_assignments')
                elif edge.kind == 'commit':
                    counter.add('commit_bitwise_or')
                    nt |= np
                    np = 0
                    counter.add('constant_fact_assignments')
            old_t, old_p = values[dest]
            counter.add('join_bitwise_or', 2)
            values[dest] = (old_t | nt, old_p | np)
    return Lifted(m, values, dict(sorted(bad_by_cost.items())), sum(len(v) for v in graph.values()),
                  plans, full, tuple(disabled), counter)
