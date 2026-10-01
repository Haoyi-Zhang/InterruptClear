# Declarative input and trusted boundary

## Model

The exact top-level keys are `id`, `title`, `initial`, `nodes`, `edges`. Identifiers and titles are nonempty strings with length at most 200. There are 1–48 nodes and at most 128 edges. A node has exactly `id`, `clean`, `pending`; its identifier is unique and at most 64 characters, and both flags are JSON Booleans. The initial identifier must name a node.

An edge has exactly `id`, `src`, `dst`, `kind`, `guard`, `reset`. Edge identifiers are unique and at most 64 characters. Endpoints must exist. The five kinds are `step`, `interrupt`, `neutralize`, `effect`, `use`. A guard is a conjunction, encoded as a list of at most eight pairs `[operator, integer]`, with operator `<`, `<=`, `==`, `>=` or `>`, and constant 0–256. An empty conjunction is true. JSON Booleans are not accepted as integers. Reset is Boolean. Neutralization edges must target a clean location. No implicit repair, pending cancellation or interrupt return is added by the tools.

There is exactly one real-valued nonnegative clock. Initially it is zero. Before every action, any nonnegative delay may elapse. An enabled action either retains the delayed clock or resets it to zero. No location invariant restricts delay. All actions count toward the event budget; only interrupt-kind actions count toward the delivery budget. The property observes the source of each use, before any edge update or reset.

The graph is already flattened. Handler phases, a pending update and nesting depth are finite location information. The schema does not claim a component product algorithm. The epoch/cancellation case distinguishes active from stale work in finite state and assumes effective cancellation; it does not implement a finite-width epoch tag or establish freedom from wraparound.

## Certificate

Both certificate kinds contain exactly `kind`, `model`, `events`, `interrupts` and one payload key. Bounds must match the invoking caller's requested bounds, not merely be smaller. The model identifier binds a name only; the verifier always reconstructs transitions from the separately supplied model. It is not a cryptographic identity or guarantee that the model is faithful.

For `kind="safety"`, `states` is a nonempty list of unique `[n,k,q,r]` tuples. The event count satisfies 0≤n≤N; the delivery count satisfies 0≤k≤min(n,K); q is a declared location; r is an integer from 0 through 2M+1. M is the largest guard constant, or zero when none occurs. r=2j denotes {j}, r=2j+1 below the tail denotes (j,j+1), and r=2M+1 denotes (M,infinity). The initial tuple is [0,0,initial,0]. Every enabled successor from n<N must be present and no such edge may be a dirty-source use. No successor obligations exist at n=N. A closed nonminimal superset is valid; the checker does not require minimality or unique witnesses.

For `kind="diagnostic"`, `steps` is a nonempty sequence of objects with exactly `edge` and `x2`. x2 is twice the clock value immediately before that edge, in half-unit integer representation, between zero and 2M+2. It is a local clock, not global time: after a reset, a subsequent value may be smaller. The checker validates connectivity, guards, nondecreasing time since reset, both budgets, and at least one dirty-source use. The generator uses the canonical representative r/2 for each region; it needs no processor addresses or program instructions.

## Limits, rejection and errors

The command-line verifier reads at most 262,144 bytes for a model and 16,777,216 bytes for a certificate. Duplicate JSON keys and nonfinite JSON constants are rejected. There can be at most 250,000 certificate states. Enabled transition obligations are capped at 500,000 per check. The experiment runner also charges aggregate semantic work. Failure of a cap or parse check is rejection/error, never safety.

No claim is made that every malformed input is covered by the test suite, or that the Python runtime is a hardened hostile-input service. Read-only semantic inspection of supplied JSON is the intended use. Concurrency/file mutation during verification is outside the experiment. The command-line byte check is not an authenticity check. The trusted computing base includes the mathematical specification, model and observation completeness, implementation logic, interpreter and ordinary local execution environment.
