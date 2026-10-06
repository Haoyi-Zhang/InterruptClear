# Deterministic semantic audit and proof domains

`audit_semantics.py` is a separate exploratory audit of the supported language.
It does not replace or enlarge the denominators of the primary campaign in
`study.py`. Its seed is 20261005 and every one of the 80 generated descriptions
is retained in `results/audit/reference.json`. Removing the model name leaves
80 distinct executable descriptions. The bounded grammar uses four locations,
three offered atoms, constants 0, 1 and 2, five original edges and zero to two
acyclic repair edges. Each effective cap is `(4,2,2)`.

The generated features include ordinary control loops, interrupt entry and
return, strict and nonzero guards, resets, destination invariants, mixed urgent
and delay-permitting locations, taint/pending sources and clears, disjunctive
commit, and zero-cost installation atoms. These are generated model-language
inputs, not a sample of deployed systems. No generated case is discarded for
its outcome or for exhausting a resource limit; an exception aborts the audit.

The actual retained run compares all eight plans for every description. For
each plan it checks every smaller nonnegative event/delivery/depth cap against
the explicit Boolean execution's complete bad-prefix cost set. It separately
compares the complete reachable Boolean state set and bad costs with the
strict difference-constraint time oracle. The symbolic producer and explicit
Boolean explorer share the region/skeleton implementation. The oracle uses a
separate time representation, but shares the intended model specification.
These are implementation cross-checks, not independent authorship, external
review, statistical generalization, or a mechanically checked proof.

| Quantity | Actual count |
|---|---:|
| Generated and unique executable descriptions | 80 |
| Model/plan comparisons | 640 |
| Plan/sub-budget assertions | 28,800 |
| Strict constraint systems | 79,080 |
| Enumerated oracle control prefixes | 11,248 |
| Reachable-state observations across model/plans | 17,986 |
| Query or oracle disagreements | 0 |
| Cases excluded by an oracle ceiling | 0 |
| Charged obligations | 145,424 |

State observations and control prefixes are summed over plans and include
repeated observations of the same model. They are not independent models.
The audit has a 150,000-obligation ceiling, a 25-second CPU ceiling and a
512-MiB address-space ceiling. Actual time and peak RSS are recorded separately
in `results/audit/measurements.json`; they do not determine correctness.

Run or replay it from the artifact directory:

```bash
python audit_semantics.py --out /tmp/icnc-semantic-audit \
  --compare results/audit/reference.json
```

The canonical JSON SHA-256 of the deterministic reference is
`4864fa063c22ddec409aad08cd77c59e0153db4043e48d2cd5775798133fc791`.
The file stores all raw model inputs, per-plan state hashes, bad resource
costs, frontiers and raw operation categories. Its successful completion is
produced by execution after all comparisons; there is no handwritten gate.

## Proof domain checks

The canonicality theorem requires the universe

`P(A) × {0,...,Nmax} × {0,...,Kmax} × {0,...,Dmax}`.

Every compared antichain must lie in that universe. Otherwise the antichains
`{(empty,Nmax+1,0,0)}` and `empty` answer every admitted smaller-budget query
identically: the extra record is never active. For retained in-cap records,
the separating query chooses the complementary plan and the record's own
resource cost, which is then an admitted query. The producer and certificate
checker already constrain every emitted or accepted record to the effective
construction cap.

The repair-word row bound `N+(N+1)L` concerns discrete rows: original actions
plus inserted repair slots. It excludes the region-delay arcs, whose count is
a separate measure. The implementation's `longest_events` function charges
repair and original edges one for that auxiliary metric and delay arcs zero.
Calling this a bound on all graph transitions would be incorrect.

For certificate adequacy, acceptance implies exact reachable states,
annotations and frontier. The finite producer conversely constructs an
acceptable rooted, topologically ordered witness when implementation limits
permit it. Semantic completeness alone does not make an arbitrary malformed
or incorrectly ordered certificate object acceptable.

The phase-erasure equality, all-plan/all-sub-budget query, fixed-context
cleanup-order criterion and threshold output family retain their declared
premises. The exploratory comparisons found no counterexample to their
implemented semantics. They do not remove the need for separate concrete
timing/resource correspondence, control independence, disjunctive transfers,
well-nested interruption and finite construction caps.
