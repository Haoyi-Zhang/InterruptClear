# Mathematical specification and proofs

These are ordinary mathematical arguments for the declared one-clock fragment, not proof-assistant-checked theorems. The core construction is a specialization of Alur–Dill regions and inductive reachability certification; it is not claimed as a novel theorem.

## Definitions

A model consists of a finite set Q with initial q0, a predicate clean:Q→{false,true}, and finite named edges e=(q,g,a,z,q'). g is a conjunction of comparisons of one clock x with nonnegative integer constants; a is the action kind; z is a Boolean zero reset. The initial clock is zero. A step from (q,x) chooses d≥0 with g(x+d), observes whether a=use and clean(q)=false, and reaches (q',0) when z holds or (q',x+d) otherwise. Delay is unrestricted, uncounted and can be zero. Only discrete actions count. Safety(N,K) says no prefix of at most N actions and K interrupt-kind edges contains a bad use. The predicate is not eventual progress or secrecy.

Let M be the maximum constant or zero. Enumerate regions R[0] through R[2M+1] as {0},(0,1),{1},…,{M},(M,∞), with representative v_r=r/2. A layered abstract state is (n,k,q,r), with n≤N and k≤min(n,K). The initial abstract state is (0,0,q0,0). There is an e-labelled transition from (n,k,q,r) through delayed region s≥r when n<N, g(v_s), and k+1[a=interrupt]≤K. Its destination is (n+1,k+1[a=interrupt],q',0) on reset or (n+1,k+1[a=interrupt],q',s) otherwise. The edge is bad exactly when a=use and clean(q)=false.

## Lemma 1: guard uniformity

For every region R[r] and guard g, all valuations in R[r] give the same truth value as v_r. Each integer comparison can change truth only at its integer boundary, which is a singleton in the partition. Between adjacent integers its truth is fixed. Beyond M, all constants lie strictly below the valuation, so truth is also fixed. Conjunction preserves equality of truth values. This handles equality, strict and weak comparisons and empty guards. QED.

## Lemma 2: ordered delay and reset

For every x in R[r] and every s≥r, some d≥0 satisfies x+d in R[s]. If s=r take d=0. If s>r, every valuation in R[s] is greater than x; choose any one and subtract x. Conversely, nonnegative time cannot move to a smaller region. A reset maps every delayed valuation to the unique region R[0]. An unchanged clock stays in its delayed region. QED.

## Theorem 1: exact bounded abstraction

Every concrete finite execution at bounds N,K has an abstract execution with the same action identifiers, counters, control locations and bad-use observations. Conversely every finite abstract execution has a concrete execution with these same quantities and the indicated regions after actions.

Proof. Map each concrete clock to its region. Lemma 2 orders its delayed region; Lemma 1 establishes the guard. The reset and counter updates agree, proving each forward step. For the reverse direction, start at concrete clock zero. Given any concrete valuation in the current abstract region, Lemma 2 supplies a suitable delay to the next selected delayed region and Lemma 1 enables the selected edge. Its reset gives the designated postregion. Repeat inductively. The bad-use observation depends only on the preserved source location and edge kind. Counters increase on exactly the same events. Thus unsafe-prefix existence agrees. The statement preserves regions, not every possible final real valuation of a fixed timed word. QED.

## Theorem 2: mathematical certificate characterization

Ignore serialization and computation caps in this mathematical statement. Let S be a finite set of legal layered states. Call S valid when (i) it contains the initial state, (ii) every allowed successor of every state in S with n<N is in S, and (iii) none of those allowed outgoing transitions is a dirty-source use. Then a valid S exists if and only if Safety(N,K).

Proof. For sufficiency, induction on abstract path length puts every reachable state in S. At an enabled next event, condition (iii) excludes a bad use and condition (ii) preserves membership. Theorem 1 transfers this to all concrete bounded prefixes. For necessity, take S to be all abstract reachable states. It is finite, initially covered and successor-closed. If condition (iii) failed at a reachable state, appending its bad edge and applying Theorem 1 would contradict Safety(N,K). At depth N no additional events are admitted; checking a fictitious N+1 event would be a different property. QED.

An implementation accepts only representations within its byte/state/work caps. Soundness of the specified acceptance predicate is preserved; computational completeness is conditional on a successful complete exploration and a representable certificate within all caps. It is not claimed for every syntactically allowed graph. The safety predicate permits redundant unreachable states when they preserve all clauses, including arbitrary legal boundary states at n=N.

## Lemma 3: canonical benign diagnostics

Every abstract violating path has a concrete witness whose preedge clock values are region representatives v_s. Consecutive representatives are nondecreasing until a reset because successive regions are ordered; resets restore zero. Lemma 1 preserves all guards, and the action sequence preserves the bad-use observation. All representatives lie at most M+1/2, so twice-values at most 2M+1 suffice. The checker also permits 2M+2, a legal integer tail witness. This is specific to one clock with no invariants or positive minimum delay; it is not a generic dense-time discretization claim. QED.

## Proposition 1: a clean return relation loses interior observations

Compare C01 and C02. Both begin dirty, neutralize to r, enter h by an interrupt, move from h to j, repair from j to k, and return from k to r. Their nodes, guards, resets, edge endpoints, event counts and delivery counts agree. The sole difference is that h→j is a use in C01 and a step in C02. All completed handler calls return clean. A summary that retains only entry/return states, total duration, action count and delivery count but erases the interior use observation is identical. C01 violates safety by its third event, whereas C02 has no dirty-source use. Therefore no Boolean decision depending only on that erased summary can be both sound and complete for this family. This is a restricted indistinguishability argument, not an impossibility of observation-preserving summaries. QED.

## Proposition 2: integer sampling and global cleanliness

In C05 neutralization resets x, an interrupt is enabled exactly for 0<x<1, and a dirty-source use is enabled for x≤1. Delays 0,1/2,0 yield a three-event violation. Integer-only preedge values never enable the interrupt, so the sampled graph incorrectly appears safe. In C06 the interrupt instead requires x>1 without resetting x, while dirty-source use requires x≤1. Once dirty, nondecreasing time makes use impossible. C06 is safe even though a dirty location is reachable. Thus always-clean is sufficient but not necessary for the use-specific assertion. QED.

## Proposition 3: completeness of a model is not certified by closure

Removing C03's delayed-effect edge, C05's interrupt edge, or C01's use observation removes its exhibited violation and yields a safe modified model at the tested bounds. The closure verifier correctly accepts the modified models, since they are its trusted input. A certificate of the modified transition system alone cannot establish that the omitted behavior is absent from another system. This follows directly from the distinct transition/observation semantics and does not depend on any exploited device. QED.

## Conditional transfer to another system

Suppose every bounded concrete prefix of another transition system has a matching abstract prefix within N,K and every concrete bad-use observation is preserved as a bad abstract use. If the abstract model is safe, the other system has no such bounded bad prefix: otherwise its matching abstract prefix is a counterexample. This contradiction proof is immediate, but its two premises are substantial obligations. This repository supplies no mapping from processor, RTL, instruction or operating-system behavior, no proof of those premises for a deployed system, and no established conversion between its event budget and another system's events. Calling its input “event complete” cannot discharge those obligations.

## Exact small oracle

For a fixed control path of n edges, introduce real event times t0,…,tn with t0 chosen as zero and nondecreasing order. If the most recent clock reset was at event j, the preedge clock at event i is ti−tj. Translate each guard into ti−tj≤c, ti−tj<c, or the reversed bound, with equality represented by both weak inequalities. Add final clock-region bounds when enumerating postregions. All constants are integers. The implementation stores a bound as (c,strict) and uses addition of c and disjunction of strictness along paths; comparisons prefer smaller c, then strict at a tie.

A negative cycle, or a zero-weight cycle containing a strict edge, is infeasible by summing its inequalities. Conversely, in their absence, replace each strict integer bound c by c−epsilon, with 0<epsilon<1/(n+1). Any simple cycle contains at most n+1 edges. A positive integer cycle remains nonnegative, and any zero cycle is wholly weak; hence the perturbed graph has no negative cycle. Shortest-path potentials satisfy its weak constraints and therefore the original strict constraints. Translation by the potential of t0 fixes t0=0. Floyd–Warshall detects the contradictory cycles. Enumerating all finite control paths and their feasible final regions therefore gives an exact bounded oracle. This oracle validates selected finite inputs; its Python implementation has not itself been mechanically verified.
