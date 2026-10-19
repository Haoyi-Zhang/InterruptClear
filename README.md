# Schedule-preserving neutralization repair

This artifact analyzes selected cleanup operations in owned finite one-clock
interrupt models. It constructs symbolic repair frontiers, checks their
certificates, and answers bounded plan-selection queries. Full mathematical
arguments are in [docs/proofs.md](docs/proofs.md).

## Requirements

Use Python 3.10 or later and the standard library. POSIX execution enforces
OS resource limits. On Windows, explicitly select `--portable`: it retains
finite operation ceilings and cooperative CPU checks, but has no OS address-space
limit or peak-RSS measurement. No network, external model service, or device is
required.

## Quick verification

Run from the artifact root:

```sh
python -B -S verify.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json
python -B -S query.py models/F02-deferred-cause.json results/primary/certificates/F02-deferred-cause.json --cap 3 0 0
python -B tests/structural_regression.py
```

The first command reparses the trusted model and replays its certificate; the
second replays before selecting least-cost safe plans at the requested cap.
The structural regression is an additional three-method control, separate from
the primary campaign and discovered-suite counts.

For the complete 80-method test suite, save new outputs outside the checkout:

```sh
python -B -S run_tests.py --portable --output /path/to/private/tests.json
```

Omit `--portable` on a supported POSIX host.

## Full reproduction

On POSIX:

```sh
sh verify.sh
```

For a retained raw workspace and output outside the artifact:

```sh
python -B -S verify_all.py --portable --keep-work --scratch /path/to/private/raw --output /path/to/private/reproduction.json
```

Use a separate output/scratch directory for optimized execution with `-O`.
The runner propagates bytecode, optimization and site-disabling flags to its
children. It runs the test suite, primary study, separate semantic audit and
configuration-lifting comparison, compares deterministic objects and references,
replays all 20 retained certificates, and checks all four phase-lowering maps.
Child commands, outputs and exit codes are retained when `--keep-work` is used.
Missing resource measurements are null and unavailable enforcement flags are false.

The scientific CI runs the POSIX reproduction and structural controls with the
same comparison/resource gates; raw command logs and campaign files are uploaded
on failure as well as success. Current hosted status is available in Actions.

## Model and result interpretation

A plan clears taint or pending data at selected sites without changing guards,
clock resets, interruption admission or control. A frontier record combines a
survival condition with original-event, delivery and peak-depth resources.
The checker determines safety for the admitted model, selected plan and cap.

Cleanup slots cost zero in original-event units, not zero instructions or time.
Their lowering exposes interruptions before, between and after cleanup. The
commit-only order result requires its stated source restrictions; new
taint-producing handlers can require additional repairs.

The producer and explicit/configuration baselines share a timing skeleton.
The checker rebuilds semantics from separate source logic, while the strict-DBM
oracle uses absolute times. These finite comparisons and written proofs do not
establish a processor-level refinement. The model requires data-independent
control, admitted fact transfers, one clock, finite bounds and well-nested
interrupts. Full schemas and resource accounting are in
[docs/schema.md](docs/schema.md) and [docs/semantic-audit.md](docs/semantic-audit.md).

## Queries, costs, and material map

`query.py --weights FILE` accepts a JSON object naming every existing atom with
an integer price in 0..256. It changes the selection objective after certificate
replay, not the trusted model, budgets, or offered clears. This is ordinary
weighted hitting-set selection; the safe-plan set is unchanged.

[docs/query-workflow.md](docs/query-workflow.md) explains the same-information
comparison and complete costs. Its retained Windows run reports 0.133 s for
frontier construction plus replay, 0.078 s for dense lifting, and 0.198 s for
explicit exploration through answers on the same cohort. Those are finite
local Python measurements, not a general speedup or hardware-defense result.

- `icnc/`: model, producer, checker, direct/lifted baselines, DBM oracle and lowering.
- `models/` and `results/primary/`: trusted inputs, certificates and primary references.
- `results/audit/` and `results/lifting/`: separately counted auxiliary studies.
- `results/query-workflow/`: normal/optimized commands, answers and complete-cost records.
- `tests/`: schema, query, interpreter-mode, orchestration and semantic controls.
- `docs/`: proofs, related work, configuration lifting, schemas and study definitions.
- `figures/draw_schematics.py`: direct Python vector diagrams for repair order
  and phase expansion. Optional Matplotlib dependency; run with `--outdir PATH`.
  Fonts are embedded and label bounds checked; no experiment or TeX is invoked.
- `claim_evidence_ledger.csv` and `external_resources.csv`: result/source mappings.

Retained older run records remain execution-time evidence; current test-method
counts and campaign denominators are reported separately by the runner.

## License and provenance

Original implementation, proof documents and results use [LICENSE](LICENSE).
Third-party publications are attributed rather than redistributed. The repair
frontier development is distinct from the older one-clock baseline.

## Portable path notation

Published execution records use `<PYTHON_ROOT>`, `<NODE_ROOT>` and `<RUNTIME_ROOT>` for local tool installations, `<DEPENDENCIES_ROOT>` for local dependencies, and `<PROJECTS_ROOT>`, `<ARTIFACT_ROOT>`, `<SOURCE_ROOT>` and `<WORK_ROOT>` for the workspace, artifact checkout, source checkout and temporary work directory of the recorded run. These are path aliases, not literal directories or claims that historical temporary files are included in this bundle. Substitute the corresponding local roots when replaying a command. Recorded tool versions, source/input identities, measurements, outcomes and failures are unchanged. Current file inventories bind the portable published bytes; any `recorded_` identity denotes pre-normalization bytes.
