# Schedule-preserving neutralization repair

This is the standalone artifact for **Schedule-Preserving Neutralization Repair under Bounded Interruptions**, developed within the Interrupt-complete neutralization contracts project. It analyzes benign, owned one-clock models; it is not a processor security evaluation.

## Reproduce the complete campaign

Requirements: Python 3.10+. POSIX mode requires `resource.setrlimit`; Windows must explicitly select `--portable`, which keeps finite operation ceilings and cooperative CPU checks but cannot enforce an OS address-space limit or measure peak RSS. No third-party Python packages, network access, external model service, device or paper directory are required.

```sh
./verify.sh
```

The script runs the discovered 63-method test suite in a child process, reruns the whole primary study, separate exploratory semantic audit and Boolean configuration-lifting comparison in fresh temporary directories, compares their deterministic JSON with the retained references, compares all model/certificate/lowering objects, separately replays all 20 retained certificates, and rechecks all four phase-lowering maps. The audit remains a separate campaign: its counts are not added to the primary model or oracle denominators. A report records the actual test count and per-campaign operations only after these actions succeed. Elapsed time and resident memory are descriptive, not reproducibility targets. Scratch files are created inside the artifact by default.

Portable local reproduction (from this directory):

```sh
python verify_all.py --portable --scratch results/repair/scratch --output results/repair/reproduction.json
```

Individual portable campaigns also accept `--portable`; write their results to `results/repair/` to preserve the retained POSIX evidence. Missing RSS is JSON null and OS-limit enforcement fields are false, not successful limit checks. The current local rerun has 63 methods (the original 61 plus two regression methods), while the three deterministic campaign references are unchanged.

Individual commands:

```sh
python3 generate_models.py
python3 run_tests.py --output results/tests-local.json
python3 study.py --output results/reproduced --compare results/primary/reference.json
python3 audit_semantics.py --out results/audit-local --compare results/audit/reference.json
python3 compare_lifting.py --primary results/reproduced/reference.json --output results/lifting-local --compare results/lifting/reference.json
python3 verify.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json
python3 query.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json --cap 3 0 0
```

## Scientific objects

A selected static repair clears taint or pending data at specified sites. It cannot change guards, clock resets, interruption admission or control. A symbolic term `F` says that a causal fact survives exactly when the selected plan intersects none of `F`. A frontier record `[F,n,k,h]` couples that condition with the original-event, delivery and **peak-depth** resources needed to reach a bad use. Plan `X` is unsafe under cap `B` exactly when an active record has `F & X == 0`.

The repair-word compiler exposes interrupts before, between and after its zero-time cleanup slots. Erasing those slots preserves the original timed event language. They cost zero in **original-event units**, not zero machine instructions or measured time. Total executed transition rows are checked separately in the retained cases; every evaluated path has at most 32 rows. An ineffective inserted operation cannot obtain apparent safety merely by pushing the original use past an instruction-count horizon.

The commit-only order result is separately checked on all 31 words of length at most four over cancellation `P` and taint clearing `C`, under all four static plans. Under the theorem's source restrictions, a safe active word contains `P` before a later `C`. Fresh taint-producing handlers require additional repairs and can make the offered plan space infeasible.

## Evidence inventory

- Twelve fixed obligations: direct and deferred causes, a bad truncated handler, a matching-return control, typed-label collision, strict open timing, infeasible timing, incomparable resource costs, peak nesting, unrepairability, alternative cuts, and disjunctive joins.
- All 64 members of a six-bit action/initial-value grammar; all are distinct after removing the name.
- Four threshold families testing the exact binomial frontier-size lower bound.
- Four independently specified repair-language lowerings.
- 5,046 exact plan/sub-budget comparisons against explicit fixed-plan execution, including all optimal-plan sets where selection is reported.
- 76 strict-difference-constraint oracle comparisons over 18 model descriptions; these are judgments, not 76 distinct models.
- 124 cleanup-word/plan checks, 360 actual budget-model copies, and 20 systematic certificate mutations plus additional malformed-input tests.
- A separate seeded exploratory semantic audit: 80 distinct model descriptions, 640 plan executions, 28,800 smaller-budget queries and full reachable-state comparison with the strict-DBM oracle. It checks resets, strict timing, arbitrary call/return control, zero-event acyclic slots and zero-cost atoms. See `docs/semantic-audit.md` for its exact denominator and independence limits.
- An owned dense Boolean configuration-lifting comparator on the same 84 primary instances: 5,046 three-way plan/budget comparisons and 526 exact optimal-plan-set comparisons against the frontier and per-plan explorer. It shares the region skeleton and tests the representation, rather than supplying a separate timing specification. This is an implementation of configuration lifting, not a reproduction of an external tool.

These are finite implementation checks, not statistical accuracy measurements. There is no learned parameter or claim that synthetic instances represent real workloads. Full proofs and adverse prior-work comparisons appear in `docs/proofs.md` and `docs/related-work.md`.

## Files and trust boundary

`icnc/model.py` defines the closed grammar and timing skeleton. `frontier.py` constructs symbolic annotations and the antichain. `direct.py` is an explicit per-plan baseline and shares the region successor function. `config_lift.py` stores one Boolean truth bit per plan and has no frontier imports; it also shares the region skeleton. `checker.py` reparses the trusted model and rebuilds successors/annotations with separate source logic; it imports none of the producer, region library, explicit baseline or oracle. `oracle.py` uses absolute event times and strict difference constraints without importing model or producer semantics. `word_interpreter.py` is a separate phase interpreter but shares region guard evaluation. `lowering.py` generates the phase model and exposes callable local correspondence obligations.

None of these programs is proof-assistant verified. Separate source logic is not independent authorship or immunity to a common specification error. The certificate checker establishes the declared model and plan/budget frontier, not completeness of that model relative to hardware. The exactness theorem requires data-independent control, constants/copy/disjunction/clear fact transfers, one clock, finite bounds and well-nested interrupts. Unknown fields, data-dependent guards, non-Boolean resets, non-integer budgets, Unicode-normalized identifier collisions and cyclic zero-base-event repair graphs are rejected.

POSIX primary study/test invocations enforce 2,500 MiB address space and 170/180 CPU seconds. The primary study has a 150,000 charged-operation cap; core and configuration test modules have separate 90,000 and 50,000 caps. The configuration comparison caps the lifted operations and frontier/explicit operations separately at 200,000 each. The POSIX semantic audit enforces 512 MiB, 25 CPU seconds and 150,000 charged operations. Portable mode checks process CPU cooperatively at metered/test boundaries, with no hard OS CPU or memory cap. The complete clean reproduction checks a 400,000 aggregate allowance and reports each campaign separately; child processes also have wall-clock timeouts. Charges count selected classes of checking operations, not every internal comparison or equivalent instruction costs. Exceeding an available cap produces no partial safe verdict.

The retained complete execution and the portable local reproduction each used 300,410 charged operations across the tests, primary study, separate semantic audit, configuration comparison and certificate replay. These are accounting values, not runtime or speedup estimates; the two new regression methods exercise unmetered validation/reporting operations and do not alter that count. The local report retains all five subtotals and the actual 63-method test report.

## Provenance and license

The current repair-frontier implementation, proof documents and primary results were recovered from the October 5 packet and edited. This development is distinct from the older one-clock baseline report; no absent earlier contract manuscript or frozen reference input is claimed recovered. The baseline PDF's standard region/certificate results are retained as attributed foundations, not renamed as new theorems. The source is licensed under `LICENSE`; third-party publications are cited rather than redistributed. Substantive ChatGPT assistance covered formulation, proofs, implementation, tests, experiments and prose. Human authors must review the work and satisfy applicable policies before external use; no author approval or venue acceptance is asserted.
