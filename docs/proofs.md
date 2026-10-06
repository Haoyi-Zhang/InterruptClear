# Proofs of the retained model-level guarantees

## 1. Domain, schedules and resource accounting

A state is `(n,k,h,q,r,stack,t,p)`. The first three coordinates record original/base events, interrupt deliveries and historical peak stack depth. `q` is finite control, `r` is one-clock region, and `t,p` are taint and pending bits. An interrupt pushes a specified continuation; a return pops. No guard or invariant refers to either fact bit or to the selected repair set. An offered repair site is a nonnegative-cost atom. Selecting it performs a pre-edge clear of the specified bit; not selecting it leaves the bit unchanged. Neither choice changes edge admission, clock behavior or control.

Ordinary and interrupt/return events consume one base event. Explicit repair slots consume none. Those slots are unconditional, clock-transparent and form an acyclic graph. Thus they cannot be used to add an infinite zero-cost computation. If `zrank` is a topological rank of zero-base-event repair edges, the tuple `(n,zrank(q),r)` increases lexicographically on every stored edge: base events increase `n`, repair edges increase `zrank`, and delay edges increase `r`. The reachable skeleton is finite and acyclic at every finite cap.

The clock partition consists of singleton constants, open intervals between constants, and the above-maximum tail. Guards and invariants are conjunctions of comparisons with these constants, so truth is uniform on each region. At a nonurgent location, any legal concrete delay passes through an ordered sequence of adjacent legal regions. Conversely, any such abstract sequence can be realized from a concrete valuation in its starting region, since intervals are ordered and nonempty. Invariants are convex conjunctions of bounds/equalities and cannot be crossed through a forbidden intermediate region. Urgent locations admit only zero delay. Resets go to the singleton zero. Induction on a control path therefore establishes exact timed feasibility of the quotient for the declared syntax. This is an instance of established one-clock region theory, not a novel quotient.

## 2. Phase lowering preserves the timed schedule language

The lowering and its checker require an uninstrumented base (no explicit repair edges or pre-edge clear annotations) and a supplied word map, including an empty map if appropriate. This is narrower than the general frontier input language, which accepts annotated models. The correspondence establishes execution of the declared words, not just existence of some schedule-preserving chain.

For each base location q carrying the finite word w_q of length l, introduce phases q_0,...,q_l. A slot q_j -> q_(j+1) performs the selected clear or identity, is unconditional and has no reset. Every phase inherits q's invariant and urgency. Every base noninterrupt edge leaves q_l; its destination is the first phase of its base destination. Every interrupt outgoing from q is copied at **each** phase. It enters the first phase of its handler and saves the interrupted phase when the specified continuation is q; otherwise it saves the first phase of that specified continuation. Returns pop these phase-valued continuations.

**Forward erasure.** Project q_j to q and each phase-valued stack entry to its base location. Remove the repair steps. Each remaining edge is a declared original edge with identical guard, reset and event label. Delay intervals respect the unchanged invariant and urgency; a zero-time removed repair is observational stutter. Interrupted and returned stacks project to the original push/pop sequence. The erased execution therefore belongs to the base timed language and has the same original-event and delivery counts and the same peak stack depth.

**Reverse lifting.** Take any finite base timed execution. At a required noninterrupt edge, finish the finite remaining repair slots with zero elapsed time, then take its copy. Before a required interrupt, choose its copy at the current phase; all phases offer that interrupt with the original guard and reset. Save and restore the prescribed phase-valued continuation. Reproduce each original delay while staying in the corresponding phase; its invariant and urgency are identical. Every base action is reproduced at its original time. Initial states and stacks correspond. This inductively lifts the entire finite trace. Repair selection affects only facts, so the argument holds for every static plan.

The local checker verifies exactly the ingredients above: complete phase chains matching the declared words; identical initial facts, constants, caps and atom costs; per-phase urgency/invariants; one copy of every appropriate original action; all interrupt copies at every phase; preserved guards and resets; first-phase destinations and saved-current-phase resumption. A successful local check implies the two constructions apply. No forward-only trace inclusion is substituted for equality.

**Row bound.** In a lowered model with maximum word length L, between original events at most L repair edges can execute. There are at most N+1 such intervals in a path of N original events. Hence total discrete rows are at most N+(N+1)L, although explicit control can give a smaller bound. The study computes the longest discrete row path in the finite skeleton, charging both base and repair edges one for this auxiliary measure, and checks that every retained evaluated instance stays within 32 rows.

**Why no generic positive-latency theorem follows.** Let a base urgent location have invariant x=0 and an outgoing edge guarded x=0. A mandatory positive-delay repair before that edge cannot preserve the original timed trace. Our theorem therefore requires zero-time abstract repair slots; applying it to machine instructions requires a separate latency/refinement mapping.

## 3. Exact symbolic facts

For a repair set X and mask F, define chi_F(X)=1 iff X intersects none of F. Interpret a term family FAM as the disjunction of chi_F over F in FAM. The empty family is false; the family containing the empty mask is true. If F is a subset of G, chi_G implies chi_F, so removing inclusion-dominated masks preserves the function.

A selected conditional clear at atom a replaces every term F by F union {a}. Its interpretation is exactly the old fact AND (a not in X). Ordinary fixed clear yields false; a fresh source yields true; copy preserves terms; disjunction unions and normalizes families. Commit updates taint by taint OR pending and clears pending. A use emits the current taint family **before** any later edge or handler return.

**Fact exactness.** At every reachable skeleton state s and for every plan X, the interpretation of its annotated taint (respectively pending) family equals the existence of a fixed-plan execution reaching s with that fact true. Initial constants establish the base. For the inductive step, transitions are admitted independently of facts and the plan, so all concrete fact valuations share the same skeleton successors. Each allowed transfer is constant/copy/disjunction/clear and distributes over existential union at joins. The local mask identities above are exact. Induction over the acyclic skeleton proves the statement. No conjunction or fact-dependent guard is admitted: either would require correlations not supplied by separate existential families.

## 4. Joint frontier theorem

On each bad-use contribution, emit a record `(F,n,k,h)`, where F is a taint-survival term and the costs are those of the post-use skeleton state. This immediately includes a bad prefix that does not return. It does not wait for an empty-stack boundary.

Order records by `(F,c) <= (G,d)` iff F is a subset of G and each cost in c is no greater than the corresponding cost in d. If `(G,d)` is admitted by budget B and survives plan X, then `(F,c)` is also admitted and survives. Removing dominated records therefore preserves all such existence queries. Let H be the minimal antichain of emitted records at construction cap Bmax.

For every X and every componentwise smaller cap B:

`Unsafe(M_X,B) iff exists (F,c) in H with c <= B and F intersect X = empty.`

**Forward.** A concrete bad prefix has a reached use whose source fact is true. Fact exactness supplies a surviving term at that use and its post-use costs. The emitted record is admitted by B. Descend through the finite product order to a minimal predecessor; that predecessor is still admitted and its smaller mask also avoids X.

**Reverse.** A frontier record is an emitted record, not a fabricated consequence. Its term surviving X witnesses an execution reaching the use with taint true by fact exactness. Event count, delivery count and peak depth are monotone, so a path ending within c <= B never exceeded B earlier. Thus the same prefix is admitted under the smaller cap and is bad. The use need not return. The monotonic historical depth h, not current depth at the use, is necessary for this step.

## 5. Canonicality and exactness separation

The record domain is explicitly `P(A) x {c in N^3 : c <= Bmax}`. Out-of-cap records are inadmissible: an obstruction at `(Nmax+1,0,0)` is invisible to every smaller-budget query and can be removed without changing an answer. The following separators require the in-cap premise.

For any retained record a=(F,c), choose X=A\F and B=c. Record a survives and is admitted. If another record (G,d) were also active on this query, G would be a subset of F and d <= c, contradicting the antichain. Removing a alone therefore changes this query's answer.

For uniqueness, take two finite antichains defining the same all-plan/all-sub-budget function. Query X=A\F,B=c for a member a=(F,c) of the first. Some member b of the second must have b <= a. Query the corresponding complement/cost of b in the first; some a' <= b. Then a' <= a. Antichain minimality forces a'=a; antisymmetry forces a=b. Repeat both ways to obtain set equality.

This is canonicality **inside the explicitly defined mask/resource query representation**, not minimum bits over every encoding. A conservative analysis may report may-unsafe more often. The result only rules out deleting a retained record while keeping every exact answer.

## 6. Repair selection and explicit output cost

At query budget B, let the active masks be those whose cost tuples are <=B. A plan is safe exactly when it intersects every active mask. Thus weighted selection is precisely a weighted hitting-set problem on those masks. This reduction and generic hitting-set optimization are established techniques; the new model object is the exact source of masks coupled to resource thresholds. An empty active mask means no offered plan repairs that causal thread. No active masks means the empty plan is safe. Enumerating all finite plans obtains the exact minimum nonnegative installation cost and all ties, without a greedy-optimality assumption.

For m atoms construct a layered choice graph selecting exactly k distinct ordered atoms before one use. Initial taint is true and each selected branch encounters the corresponding conditional clear. Each k-subset yields mask F with |F|=k and the same cost (m+1,0,0). No different k-subsets dominate each other, so the frontier has binomial(m,k) records. A plan hitting all k-subsets must leave fewer than k atoms unselected, hence has at least m-k+1 selected atoms; every such plan suffices. For k near m/2, this gives an exponential explicit-output lower bound on a polynomial-size skeleton. It does not exclude a different symbolic representation with a smaller description for this regular family.

## 7. Preemption-sensitive cleanup order

Let initially taint=pending=1. Consider a finite straight-line active word over P (clear pending) and C (clear taint), followed by use. Interference can execute commit-and-return at every word boundary, including before/after the word; it creates no new source except commit's transfer of pending to taint. The resource envelope admits the original use and one such handler execution. Then every admitted use is safe iff the active word contains P before a later C.

**Sufficiency.** After that P, pending remains false because no fresh schedule source exists. A later C clears existing taint. Every subsequent P/C is harmless and every subsequent commit sees pending false, so use is untainted. Earlier commits are repaired by that C.

**Necessity.** If no C is active, initial taint survives. Otherwise choose the last C. If there is no earlier P, pending either remains true until a chosen interrupt or has already committed; select a schedule with no earlier interrupt and commit immediately after the last C and before any later P (or before use if no P follows). This admitted commit recreates taint, and no later C exists. The use is bad. Hence safety requires a P preceding a later C.

The test suite checks all words of length <=4 and all four selections. The theorem itself concerns arbitrary finite words satisfying its assumptions; it is not an unbounded-resource or arbitrary-handler guarantee. Fresh arm/schedule sources invalidate the sufficiency premise; the nonrepairable/repaired-return controls make that distinction explicit.

## 8. Certificate adequacy

The certificate lists every reached skeleton state, an earlier-index predecessor witness for each nonroot state, and exact symbolic taint/pending annotations. Parent witnesses show every listed state is genuinely reachable. Initial equality and successor closure show every reachable state is listed. Strict topological order prevents cyclic witness justifications. The checker independently rebuilds every successor and the local symbolic recurrence, requiring exact annotation equality. Finally it rebuilds all bad records and their product-minimal antichain, requiring exact frontier equality.

Therefore acceptance implies the supplied frontier answers precisely the declared plan/budget queries, subject to the mathematical algorithms and input assumptions. Conversely, the finite construction produces such a certificate when it fits the implementation limits. Mere safe over-approximation is not sufficient for exact optimality or irredundancy claims; the reachability witnesses and annotation equalities supply the reverse direction. The Python code and checker are not mechanically verified.

## 9. Independent time checking and concrete transfer

The strict-DBM oracle introduces absolute times for actual transition rows, a reset index and nondecreasing-time constraints. Guards/invariants become differences between event times and the last reset. Equalities use two weak inequalities. Strictness is propagated by disjunction along paths. A negative or strict-zero cycle is inconsistent. Conversely, for a finite integer-weight system with no such cycle, replace each strict bound c by c-epsilon for sufficiently small positive epsilon; positive-weight simple cycles remain positive and zero cycles are all weak. Shortest-path potentials satisfy the perturbed system, hence the original strict constraints. Region constraints recover full reachable post-clock regions. This independently structured check still shares the intended model specification and is not independent authorship.

For an external defense, a separate relation must map initial states, simulate caller/interrupt segments, preserve well-nested behavior and peak-depth/delivery accounting, bound original-event usage, and reflect every concrete violating observation into an abstract tainted use. If the chosen plan hits all active frontier masks and these conditions hold, a concrete bad prefix would map to an admitted abstract bad prefix, contradicting the query theorem. No such processor, RTL or operating-system relation is supplied. The owned repair-language lowering discharges a language-to-language correspondence, not that external obligation.
