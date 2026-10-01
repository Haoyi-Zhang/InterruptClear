# Closest-work boundary and reading scope

The full external-resource ledger contains the official/scholarly URLs, dates, read scopes and license treatment. No source attack repository, executable baseline, processor trace or RTL was acquired. The only experimental inputs are the original JSON models in this repository. Public papers motivate and delimit the question; they are not validation data.

## Origin

The USENIX primary record identifies **Daniël Trujillo and Mengjia Yan**, in that order, as authors of *TONTOU: On the Exploitability of Time-of-Neutralization to Time-of-Use Windows*, USENIX Security 2026, pp.477–495. The conference date is August12–14,2026. The relevant distinction is between neutralization and later consumption. Its mitigation discussion already includes re-neutralization; that idea is not claimed here as original. Its experimental conclusions concern the systems it examined. They supply no automatic refinement map to our graphs. Main sections1–10, ethical discussion and bibliographic material were inspected through the readable PDF; no operational attack content was integrated or executed.

## Decisive formal-methods comparison

Alur and Dill, *A Theory of Timed Automata* (1994), sections4.2–4.3, establishes the region foundation. Our one-clock ordered intervals are a restricted specialization, not a new finite-abstraction principle.

Wimmer and von Mutius, *Verified Certification of Reachability Checking for Timed Automata* (TACAS2020), final publisher pp.425–429, explicitly gives the initial/closure/nonbad certificate recipe at p.426. Its general certification work is stronger than the present bounded Python baseline in implementation assurance. An earlier author manuscript retrieved during intake has a different title, *Towards Practical Verification of Reachability Checking for Timed Automata*. The final publisher chapter was retrieved and used to resolve that discrepancy; the two titles are not silently conflated. No source code from either work was imported.

Wimmer and Lammich, *Verified Model Checking of Timed Automata* (TACAS2018), was checked through its abstract/introduction and verified bibliographic record for the contrast with mechanical verification. It was not treated as a completed full-paper calibration reading.

## Nearby speculative-contract work

Guarnieri, Köpf, Reineke and Vila's *Hardware-Software Contracts for Secure Speculation* has an author record identifying the S&P2021 paper. It establishes prior contract framing. The claim used here is that narrow framing, not a reconstruction of its formalization.

Tan, Yang, Bourgeat, Malik and Yan's *RTL Verification for Secure Speculation Using Contract Shadow Logic* was checked against the arXiv record and first-page introduction. The record reports ASPLOS2025 acceptance. The bibliography intentionally cites the accessible author preprint and does not invent proceedings pages. Its RTL evaluation is source-reported and not reproduced here.

Lau, Erbsen and Chlipala's *Granite* is a July29,2026 preprint. The abstract, limitations in section1, interrupt treatment in section4.1 and guarantee framing in section4.3 were inspected. It precludes a broad novelty claim based only on adding interrupts to contracts. It is not claimed to verify every processor or every side channel, and its proofs were not executed here.

## Assessment

The implemented certificate and its one-clock fidelity argument are a transparent baseline, not an established original research advance. The controls provide useful local falsifiers but do not prove practical significance. No thorough twelve-paper TDSC, five influential-paper and five adjacent-paper writing calibration was completed. This targeted comparison is sufficient to withhold the specific novelty claim; it is not a comprehensive literature survey or evidence that no stronger formulation can succeed.

PDF text was read through the web reader. Direct source-PDF acquisition into the working container failed, so no redistributed full-paper copies are included. This does not affect standalone reproduction because no experiment depends on those files. Exact future replication of the web-reading presentation itself is not claimed.
