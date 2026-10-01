# Interrupt-complete neutralization

An exact, bounded **one-clock baseline** for protected-use assertions in owned abstract defense automata. This repository is a technical feasibility result, not a new timed-automata theorem, a verified processor defense, or a completed journal research contribution.

All twelve experimental inputs are original, self-contained declarative graphs. There are no executable vulnerability cases, device interfaces, network operations, private data, external solvers, or model-service dependencies.

## Reproduce

Use Python 3.10 or newer and its standard library on a POSIX system with the `resource` module. Run from this repository root:

```sh
python3 run_tests.py --output results/reproduced-tests.json
python3 reproduce.py --output results/reproduced --compare results/reference.json
python3 verify.py models/A01.json results/certificates/A01.json --events 32 --interrupts 8
```

The first command exercises 37 test methods, including 22 selected malformed-input controls. The second runs the frozen experiment and compares **every deterministic result field**, not timings, with the retained reference. It exits unsuccessfully on any disagreement. The last demonstrates direct verification against the caller-supplied model and bounds. These commands do not need the paper, a cache, downloaded source papers, a server, or a linked account. They write only the explicitly named result destinations.

The measured campaign uses one worker. The reproduction and test runners impose a 2,500 MiB address-space cap and a 170-second soft / 180-second hard CPU cap. They are not sandboxing interfaces for arbitrary untrusted programs. Exploration caps raise an error rather than declaring safety. Pure mathematical completeness is conditional on sufficient resources in this implementation; the entire accepted input grammar is not claimed to fit the campaign budget.

## What is checked

A model has a single dense-time clock, reset only to zero, and integer guard constants. Every action consumes one event. Only an `interrupt` edge consumes one interruption delivery. Time delay consumes neither counter. A violation is a `use` edge taken from a location whose `clean` flag is false. A dirty location without a feasible use is not by itself a violation. The `pending` flag documents an interpretation but has no hidden transition semantics.

The fixed full bounds are 32 events and eight deliveries. Seven models satisfy the assertion and five violate it. The full searches visit 10,847 layered region states and enumerate 37,840 enabled transition obligations. An independent algorithm based on strict difference constraints agrees on the entire reachable-state sets of all twelve models at six events and two deliveries. This is finite differential validation, not a machine-checked general proof or independent human review.

Important discriminators are an interior handler use, a delayed update after neutralization, a strictly fractional interruption window, and a failure requiring two deliveries. Omitting a behavior from the **model** can produce an honestly verified but irrelevant certificate. The verifier cannot recover events that its trusted model does not declare.

## Contents

`solver.py` generates reachable-state certificates or benign diagnostic paths. `verify.py` implements schema and certificate checking without importing the generator or oracle. `oracle.py` enumerates control paths and decides dense-time feasibility with strict difference constraints, without importing either region implementation. `protocol.json` fixes selection, bounds, controls and budgets. `models/` holds all exact inputs. `tests/` holds the unit tests. `results/` holds the primary reference, certificates, pilot measurements, test summary and clean-reproduction record. `docs/` provides the mathematical specification, proof and case catalogue. The two CSV ledgers separate proof, computation, source evidence and unresolved claims.

The JSON reference and CSVs preserve scientific results, not software fingerprints. Reproduction compares semantic results. Runtime measurements are descriptive single executions and are not performance comparisons or speedup estimates. No random seeds are involved. Malformed-case rejection work can also vary with set visitation order: it is a resource observation, not a deterministic semantic field. The retained clean record reports both observed rejection-work totals; all expected test outcomes and every fixed-protocol reference field agree.

## Evidence and limitations

Read `docs/proofs.md` for the complete model-relative argument and `docs/schema.md` for the trusted input boundary. The exact one-clock quotient and inductive certificate are specializations of established timed-automata and certification principles; see `docs/literature.md`. The general proofs are written mathematical arguments, not Isabelle/Rocq/Lean developments. Separate source logic can still share a conceptual mistake.

There is no hardware refinement relation, information-flow proof, eventual-use guarantee, availability claim, unbounded interrupt theorem, arbitrary nesting theorem, or four-clock implementation. The case catalogue is designed validation coverage, not a sample of deployed systems. No instructions should be inferred for changing deployed defenses.

## License and provenance

Original code, models, tests, result data and documentation are available under the accompanying MIT license. No upstream executable code or source-paper figures are included. Scholarly algorithms are attributed in `docs/literature.md` and `external_resources.csv`. Substantive model design, arguments, source code, tests and documentation were generated with OpenAI ChatGPT (GPT-6 Astra Pro); they must not be represented as human-only work. No independent author approval or external peer review is asserted.
