# Complete model catalogue

All cases are owned declarative abstractions. C means clean, D means dirty; P means a pending effect is declared, and – means none. Pending annotations have no implicit semantics. N=32, K=8 in the full study; arbitrary nonnegative delays are admitted before every edge. Empty guard is true. Only interrupt-kind edges increment the delivery count. Each edge increments the event count.

## A01 — Guarded protected use

Initial: `d`. Full verdict: safe. Use is disabled in every dirty state.

Locations: d: D/–, c: C/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | c | neutralize | true | zero |
| i | c | d | interrupt | true | retain |
| u | c | c | use | true | retain |
| w | d | d | step | true | retain |

## A02 — Repair on handler return

Initial: `d`. Full verdict: safe. Handler returns only after its repair, and no nested delivery is declared.

Locations: d: D/–, r: C/–, h: D/–, k: C/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i | r | h | interrupt | true | retain |
| repair | h | k | neutralize | true | zero |
| return | k | r | step | true | retain |
| u | r | r | use | true | retain |
| wait | h | h | step | true | retain |

## A03 — Drain before neutralization

Initial: `p`. Full verdict: safe. Neutralization has no outgoing edge from a pending-effect state.

Locations: p: D/P, d: D/–, r: C/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| effect | p | d | effect | [['>=', 2]] | retain |
| n | d | r | neutralize | true | zero |
| i | r | p | interrupt | true | zero |
| u | r | r | use | true | retain |
| wait | p | p | step | true | retain |

## A04 — Logical cancellation of stale effects

Initial: `p`. Full verdict: safe. A canceled pending update is explicitly unable to dirty the state. This is an assumption, not a counter-width proof.

Locations: p: D/P, s: C/P, r: C/–, d: D/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | p | s | neutralize | true | zero |
| drop | s | r | effect | [['>=', 1]] | retain |
| i_s | s | p | interrupt | true | zero |
| i_r | r | p | interrupt | true | zero |
| u_s | s | s | use | true | retain |
| u_r | r | r | use | true | retain |
| commit | p | d | effect | [['>=', 1]] | retain |
| n_d | d | r | neutralize | true | zero |

## C01 — Dirty interior use with clean return

Initial: `d`. Full verdict: unsafe. Checking only the handler return omits a bad interior prefix.

Locations: d: D/–, r: C/–, h: D/–, j: D/–, k: C/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i | r | h | interrupt | true | retain |
| interior | h | j | use | true | retain |
| repair | j | k | neutralize | true | zero |
| return | k | r | step | true | retain |
| u | r | r | use | true | retain |

## C02 — Clean return without interior use

Initial: `d`. Full verdict: safe. Same timed state path and return relation as C01; interior event is not a protected use.

Locations: d: D/–, r: C/–, h: D/–, j: D/–, k: C/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i | r | h | interrupt | true | retain |
| interior | h | j | step | true | retain |
| repair | j | k | neutralize | true | zero |
| return | k | r | step | true | retain |
| u | r | r | use | true | retain |

## C03 — Pending effect survives neutralization

Initial: `p`. Full verdict: unsafe. Cleaning visible state does not cancel a declared pending update.

Locations: p: D/P, r: C/P, d: D/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | p | r | neutralize | true | zero |
| effect | r | d | effect | [['>=', 2]] | retain |
| u | r | r | use | true | retain |
| bad | d | d | use | true | retain |

## C04 — Explicit pending cancellation

Initial: `p`. Full verdict: safe. The pending update is modeled as canceled and preserves the clean predicate.

Locations: p: D/P, r: C/P, c: C/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | p | r | neutralize | true | zero |
| effect | r | c | effect | [['>=', 2]] | retain |
| u | r | r | use | true | retain |
| after | c | c | use | true | retain |

## C05 — Strict sub-tick delivery window

Initial: `d`. Full verdict: unsafe. Integer-only time exploration misses the open interval (0,1).

Locations: d: D/–, r: C/–, h: D/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i | r | h | interrupt | [['>', 0], ['<', 1]] | retain |
| u | r | r | use | [['<=', 1]] | retain |
| bad | h | h | use | [['<=', 1]] | retain |

## C06 — Delivery after the use window

Initial: `d`. Full verdict: safe. A dirty state is reachable, but every dirty use is timing-infeasible.

Locations: d: D/–, r: C/–, h: D/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i | r | h | interrupt | [['>', 1]] | retain |
| u | r | r | use | [['<=', 1]] | retain |
| bad | h | h | use | [['<=', 1]] | retain |

## C07 — Two-delivery threshold

Initial: `d`. Full verdict: unsafe. One-delivery safety does not extend to two deliveries.

Locations: d: D/–, r: C/–, s: C/–, h: D/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i1 | r | s | interrupt | true | retain |
| i2 | s | h | interrupt | true | retain |
| u_r | r | r | use | true | retain |
| u_s | s | s | use | true | retain |
| bad | h | h | use | true | retain |

## C08 — Nested delivery after outer repair

Initial: `d`. Full verdict: unsafe. A repair before a nested delivery does not justify the outer return.

Locations: d: D/–, r: C/–, o: D/–, k: C/–, h: D/–, j: D/–, f: D/–

| Edge | Source | Destination | Kind | Guard | Reset |
|---|---|---|---|---|---|
| n | d | r | neutralize | true | zero |
| i1 | r | o | interrupt | true | retain |
| repair | o | k | neutralize | true | zero |
| i2 | k | h | interrupt | true | retain |
| inner_return | h | j | step | true | retain |
| outer_return | j | f | step | true | retain |
| normal_return | k | r | step | true | retain |
| u | r | r | use | true | retain |
| bad | f | f | use | true | retain |

