# Schedule-preserving neutralization repair

This is the standalone artifact for **Schedule-Preserving Neutralization Repair under Bounded Interruptions**, developed within the Interrupt-complete neutralization contracts project. It analyzes benign, owned one-clock models; it is not a processor security evaluation.

## Reproduce the complete campaign

Requirements: Python 3.10+. POSIX mode requires `resource.setrlimit`; Windows must explicitly select `--portable`, which keeps finite operation ceilings and cooperative CPU checks but cannot enforce an OS address-space limit or measure peak RSS. No third-party Python packages, network access, external model service, device or paper directory are required.

```sh
./verify.sh
```

The script runs the discovered 80-method test suite in a child process, reruns the whole primary study, separate exploratory semantic audit and Boolean configuration-lifting comparison in fresh directories, compares their deterministic JSON with the retained references, compares all model/certificate/lowering objects, separately replays all 20 retained certificates, and rechecks all four phase-lowering maps. The audit remains a separate campaign: its counts are not added to primary model or oracle denominators. A report records the actual test count and per-campaign operations only after these actions succeed. Elapsed time and resident memory are descriptive, not reproducibility targets. Scratch files default to the artifact directory; select a private external `--scratch` location to preserve a read-only checkout. Pass `--keep-work` to retain raw campaign files on success or failure. Each child command records its literal arguments, exit code and output. The semantic audit writes its observation before its equality gate.

Portable local reproduction (from this directory):

```sh
python -B -S verify_all.py --portable --keep-work --scratch /path/to/private/raw --output /path/to/private/reproduction.json
python -B -S -O verify_all.py --portable --keep-work --scratch /path/to/private/raw-optimized --output /path/to/private/reproduction-optimized.json
```

Set `PYTHONDONTWRITEBYTECODE=1` for owned subprocesses. The runner propagates bytecode, optimization and site-disabling flags to its scientific children. Individual portable campaigns accept `--portable`; write new attempts outside this repository. Missing RSS is JSON null and OS-limit enforcement fields are false, not successful limit checks. `results/query-workflow/` contains the current normal and optimized 80-method executions, fresh raw campaign data, literal command receipts, environment, common query answers and source bindings. Both modes reproduce the same retained semantic references; modes are not pooled. Earlier 61-, 63- and 66-method results and raw timings remain unchanged historical evidence, not measurements of the new controls.

The prepared `scientific-checks.yml` workflow runs from this flat artifact root on Ubuntu 24.04 for pushes to `main` or manual dispatch. It retains the existing comparison/failure gates, limits the whole command to 650 seconds and 2,500 MiB address space, and always attempts to upload its command log and raw campaign files. It has not been executed remotely by this repair worker. This workflow does not build the sibling paper or establish hardware refinement.

Read-only query commands (full campaign inputs are generated in the private scratch directory above):

```sh
python -B -S verify.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json
python -B -S query.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json --cap 3 0 0
python -B -S query.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json --cap 3 0 0 --weights /path/to/private/weights.json
```

## Scientific objects

An explicit optional portable structural regression runs with
`python -B tests/structural_regression.py` from any working directory. The
scientific CI runs this step before full reproduction and retains its log.
Its three methods are deliberately outside the historical and current suite/campaign accounting;
all existing expected counts, comparisons and resource gates remain active.
The reference uses raw tables and rational representatives, plus bounded
strict-DBM controls. Producer and both shared-skeleton baselines now prepare
invocation-local read-only indices only for recursively immutable model fields;
hand-built models with mutable fields keep fresh reads. Public properties still
return fresh containers, and the separate-source checker is unchanged.
This is implementation conformance, not a timing or new scientific guarantee.

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

The retained complete execution and earlier portable local reproduction used 300,410 charged operations across the tests, primary study, separate semantic audit, configuration comparison and certificate replay. The subsequent 66-method portable run uses 300,437: the name-boundary regression adds 27 metered obligations, while the two raw-retention regressions are unmetered orchestration checks. These are accounting values, not runtime or speedup estimates. All five subtotals and the raw workspace path are reported by a fresh `--keep-work` run; primary, audit, lifting and replay subtotals are unchanged.

The current 80-method runs also report 300,437 selected-operation charges. The new query/schema, objective-reuse and interpreter-mode controls are included in test execution and CPU time, not added to those historical core/configuration operation categories or to scientific model counts. Numeric scientific reference comparisons use canonical JSON rather than Python's Boolean/integer/float coercive equality. Query masks and caps require exact integers; model-bound queries reject out-of-universe masks and caps beyond the certified construction domain. A bare frontier tuple has no model identity: use the frontier of the same admitted model, or replay the certificate first.

## Installation objectives and complete costs

`--weights` is a JSON object naming exactly the existing atoms with integer prices in 0..256. It changes only the selection objective after full certificate replay; it does not change offered clears, executable semantics, budgets or the certificate's trusted model binding. For F02, `{ "C": 1, "P": 2, "U": 1 }` selects `{U}` at cost 1 instead of the original cost-3 tie `{C,P}` / `{U}`. The five safe plans are unchanged. All zero-cost ties are retained. This is reuse of ordinary weighted hitting-set selection, not a new optimization theorem.

`profile_workflow.py` provides a fresh-process arm for `frontier`, `lifting` or `explicit`; its `--primary`, `--output` and `--portable` options select the unchanged cohort, a private output directory and portable limits. See `results/query-workflow/commands/profile-*.json` for literal executed commands and `docs/query-workflow.md` for the complete method. The same 84 models, 652 plans, 5,046 safety queries and 526 optimal-plan-set queries produce byte-identical answers in all three arms. In one actual Windows 11 / Intel Core i7-12700KF / CPython 3.12.14 run, wall time through answers was 0.133 s for frontier construction plus complete certificate replay, 0.078 s for dense lifting, and 0.198 s for explicit exploration. Whole child wall times, own-process peaks and every stage are retained. The frontier arm was slower than dense lifting; no general runtime or memory superiority is inferred. All arms supply the same query guarantee, while the frontier arm additionally emits and replays an explanation certificate. These are actual local Python finite-model executions, not native processor defenses, production traces or executions of external research tools.

## Provenance and license

The current repair-frontier implementation, proof documents and primary results were recovered from the October 5 packet and edited. This development is distinct from the older one-clock baseline report; no absent earlier contract manuscript or frozen reference input is claimed recovered. The baseline PDF's standard region/certificate results are retained as attributed foundations, not renamed as new theorems. The source is licensed under `LICENSE`; third-party publications are cited rather than redistributed.

Substantive ChatGPT assistance covered formulation, proofs, implementation, tests, experiments and prose. Human authors must review the work and satisfy applicable policies before external use; no author approval or venue acceptance is asserted.
