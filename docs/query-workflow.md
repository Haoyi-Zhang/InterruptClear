# Same-query workflow and installation objectives

The existing 84-instance primary cohort supplies the common admitted model inputs. Its 652 plans yield 5,046 safety queries over all smaller budgets and 526 weighted-optimum queries, including every minimum-cost tie. `profile_workflow.py` executes one selected arm per fresh local process, with the same input and canonical answer encoding:

- `frontier`: construct all symbolic annotations and the frontier, emit a certificate, replay the complete certificate through the separate-source checker, then query safety and weighted optima.
- `lifting`: construct dense all-plan Boolean annotations, then answer the same safety and optimum queries. It shares the region skeleton, not frontier annotations or the certificate consumer.
- `explicit`: explore every fixed plan, retain those exploration results, and reuse their safety bits for selection. This implementation retains diagnostic exploration data; it is not an optimized memory lower bound.

All three canonical answer streams have SHA-256 `a91031246b3ec38386ff76072789482651ef05cf0e56644daceaf563323a9454`. The frontier's certificate is an additional explainable output, not a stronger safety guarantee than the common exact query contract. Safety and optimum stages follow the actual APIs: dense lifting batches plan truth bits, and explicit selection reuses its computed safety bits. No deliberately weakened baseline repeats exploration for every query.

## Measured boundary

`results/query-workflow/profile/` contains the actual arm receipts with input decoding, admission, complete construction, certificate replay where applicable, all safety queries, all optimum queries, answer encoding/write, and source-binding costs. `summary.json` distinguishes wall time through answers from the externally measured whole child process, including interpreter startup, imports, metadata/receipt I/O and exit. CPU timings are coarse process-clock measurements; zero-valued stages do not mean zero work. One sequential run per arm is descriptive, not a speedup estimate or statistical ranking.

The actual host was Windows 11 Professional 10.0.28000, Intel Core i7-12700KF, with CPython 3.12.14 and no scientific third-party packages. `environment.json` binds the local observation. Windows peaks use `GetProcessMemoryInfo` on the current process pseudohandle only, observed before receipt write and process exit. They are neither Linux peak RSS nor enforced OS memory caps. Portable resource reports retain false hard-limit enforcement and null RSS. Every arm has a 200,000 selected-operation ceiling and cooperative CPU checks; these operation categories are not equal-cost machine instructions.

Through-answer wall times were 0.132592 s (frontier plus full replay), 0.078248 s (dense lifting) and 0.198222 s (explicit). Whole-child wall times were 0.599787, 0.441038 and 0.527613 s respectively. The frontier is slower than dense lifting in this run. Its 22.68 MiB own-process peak versus lifting's 22.81 MiB is not evidence of memory superiority; explicit's 29.72 MiB includes retained diagnostics. No SPLlift/BDD, IF, UPPAAL, TarTar, processor, RTL, OS refinement or side-channel tool was executed.

## Reusing the selection objective

The trusted model's original prices remain part of certificate replay. A query-only price object names exactly the existing atoms and gives exact integer prices from 0 through 256. It changes only the weighted objective over the existing feasible set. This is the same ordinary hitting-set optimization used by the original theorem, including all zero-cost ties; it neither changes the repair language nor adds a scientific expressiveness claim.

In existing F02, the original prices C=1, P=2, U=3 give the cost-3 tie `{C,P}` and `{U}`. With query-only U=1, `{U}` is the unique cost-1 optimum. Both calls have the same five safe plans. Mutating an embedded model price still invalidates the original certificate. A lower cap must lie inside the model's construction cap, and a model-bound plan must use only offered atoms. Bare frontier tuples do not encode a model identity or a certified cap; use the admitted model that produced them or the full certificate replay path.

## Current evidence and historical measurements

Normal and optimized complete reproduction each execute the same 80 discovered test methods and the unchanged primary, exploratory audit and lifting campaigns; modes and separate structural controls are not pooled. New API/schema and objective controls do not inflate model/query denominators. Each run retains all 20 certificate replays and four lowering checks. The selected-operation subtotal remains 300,437 because the new controls are not charged as historical core/configuration categories; they are included in actual test CPU execution.

`results/query-workflow/` contains the current answer stream, profiles, raw campaign observations, command receipts, summary, environment and `bindings.json`. Commands record observed red/green controls, not a new scientific matrix. Public paths use `$PROJECT` / `$OWNED_OUTPUT`; numeric observations and source hashes are retained. `bindings.json` names the eight local modules imported by the profiler and the original cohort input. Import membership is not function-level coverage or independent authorship. Earlier `results/primary`, `results/audit`, `results/lifting` and other measurement records remain unchanged historical evidence. Finite conformance, successful builds or CI do not establish research novelty, hardware transfer, human approval or venue acceptance.
