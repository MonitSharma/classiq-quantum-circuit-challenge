# Research review of the Classiq logo oracle

The best supported next direction is **small, context-aware unitary synthesis of shared predicates and phase operations**, with explicit workspace invariants and complete-circuit depth accounting. More transpiler seeds, independent Boolean-factor minimization, or another direct truth-table expansion are poorly supported by the existing results. No publicly accessible winning circuit or demonstrated sub-150 implementation was located in the searches, and the available literature does not establish that this particular target admits depth below 150.

The protected local artifact remains **524 depth, 950 CX, 18 qubits**. Its file and exhaustive-report hashes match. The live challenge page inspected in Safari on September 9, 2026 shows Daksh S. leading at **197 / 475 / 18**, and “Monit S.” at rank 21 with **531 / 1020 / 18**. The latter name and metrics match this workspace's packaged predecessor, but the page alone does not authenticate account ownership. Older statements that nothing has been submitted are no longer a reliable description of the public leaderboard. [1: Classiq challenge](https://www.classiq.io/challenge#leaderboard)

## Target and evidence standard

The required action is

\[
U_f|x,y,0^6\rangle=(-1)^{f(x,y)}|x,y,0^6\rangle,
\]

up to one common global phase. The predicate is the union of the square `[2,26] × [29,53]`, bar `[26,49] × [39,43]`, and disks `(x−55)²+(y−41)² ≤ 42` and `(x−40)²+(y−19)² ≤ 72`. It marks 1,097 of 4,096 coordinates. The local authoritative implementation is `src/search.py`; the original notebook independently describes the rectangle baseline and standalone verification requirements.

Official scoring uses U3/CX depth under all-to-all connectivity, then CX count to break equal-depth ties, with width capped at 18. The page lists September 30, 2026 as the closing date. An improvement to 196 would beat the currently observed depth; 150 is a stretch target, not a requirement for passing today's leader. Neither score would guarantee the final September 30 ranking. [1: Classiq challenge](https://www.classiq.io/challenge#leaderboard)

The essential distinctions are full oracle versus component, exact serialized gates versus abstract gates, and numerical equivalence versus classical truth-table equivalence. T-depth, AND count, BDD size, QROM query complexity, and raw SDK depth can guide a search, but none is the challenge score.

## Repository audit

The audit covered the handoff, experiment history, current design, latest reassessment, original notebook text, current generator and feature encoding, MCZ helper, cofactor emitter, verification code, and protected QASM/report. The local checkout was at `dbfa448` when inspected. Public GitHub retrieval through the search service failed, so code findings are grounded in the supplied local checkout rather than an assertion that the remote tip was independently synchronized.

The measured protected file is `artifacts/524/full_mux_feature_linear_tket_524.qasm`, SHA-256:

```text
7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147
```

Its existing report covers all 4,096 clean-ancilla basis inputs, with maximum error about `1.11e−13`, ancilla error about `1.84e−14`, and a discarded-amplitude bound about `2.28e−13`. This review remeasured the gates and checked the report hash; it did not rerun that exhaustive simulation or replace the QASM.

The actual lineage is the six-feature `full_mux` construction, physical feature reassignment, affine encoding with matrix rows `(9,23,21,8,17,32)`, then pytket post-processing. Describing the current 524 artifact as merely seed 94 followed by peephole optimization omits the affine encoding step.

| Family | Representative complete result: depth / CX | Interpretation |
|---|---:|---|
| Original notebook | 5,329 / 3,502 | Recorded baseline |
| XAG rank construction | 1,046 / 903 | Verified, substantial recomputation |
| Corrected pair construction | 779 / 736 | Verified; older apparent 688 result invalid |
| Shared radius UCR | 682 / 740 | Verified architectural improvement |
| Six-feature parallel UCR | 536 / 1,020 | Verified main breakthrough |
| Affine features plus pytket | **524 / 950** | Current protected local best |
| Disjoint geometry plus sharing/cleanup | 649 / 727 | Verified but deeper |
| Shannon radius split | 969 / 1,244 | Verified; extra sweeps erase savings |
| QROM tree | 777 / 606 | Verified; low CX does not imply low depth |
| Persistent output-frame loader integration | 2,032 / 1,425 | Verified; still heavily serialized |
| Threshold-feature oracle | 781 / 1,318 | Verified comparator removal loses overall |
| Complete cofactor phase integration | 1,685 / 1,026 | Verified; component improvements do not transfer |
| Direct global phase cubes | 1,725 / 1,235 | Verified; expensive unshared phase conditions |

These values are repository evidence, not new benchmark runs. For detailed provenance and invalid historical variants, retain `docs/EXPERIMENTS.md` and `docs/HANDOFF.md`.

The main reason so many trials fail is now clear: a classical expression is optimized first, and only afterward its temporary values must be made reversible with six ancillas. The resulting recomputation and serialization often dominate. Conversely, the current UCR architecture spends more CX but schedules its outputs well, which is why it wins locally.

## What actually prevents another small tweak from winning

The original construction pays roughly three 128-layer stages: y-feature loading, x-controlled phase application, and inverse loading. Folding, comparison, guarded phase, and the radius-eight correction add further work. These stage numbers describe the existing construction, not a universal complexity theorem.

The new audit counts **405 operations on q16** in the protected 524 file. Because a qubit cannot participate in two gates in the same layer, 405 is a lower bound for scheduling that fixed gate multiset. Reordering its gates cannot reach 197. Passing below 197 requires changing or eliminating substantial work on that wire; gate identities and resynthesis can do this, so 405 is not a lower bound for the target unitary.

CX count is a useful diagnostic, but it is **not the primary binding constraint imposed by the rules**. A 196-depth circuit with more than 475 CX would still beat the current 197-depth entry. A design should therefore retain candidates on a depth/CX Pareto frontier instead of discarding every circuit above the leader's CX count.

The old reassessment's argument that 197/475 reveals three five-control UCR stages is an architectural guess. Similar aggregate numbers can arise from many decompositions. Likewise, one can exclude the present three-full-sweep design without excluding every possible use of a six-control UCR inside a winning circuit.

## Research findings and their applicability

### Uniformly controlled rotations and phase-tolerant loading

Bergholm, Vartiainen, Möttönen and Salomaa give the foundational uniformly controlled gate constructions. They explain why truth-table-controlled single-qubit operations admit regular decompositions, but their general upper bounds do not prove optimality for this structured Boolean oracle. The current code already implements a regular Gray/Walsh sweep with shared scheduling. [2: Uniformly controlled gates](https://arxiv.org/abs/quant-ph/0410066)

Seidel and colleagues develop phase-tolerant logic synthesis for computed labels that are later uncomputed. Their savings compare against fully specified phase-correct loading; the published halving must not be applied again to a loader that already tolerates phases. Here `RY(π f(y))` maps a clean output to the correct bit, and the exact inverse cancels permissible phases. This paper is useful for deriving safe variants, not evidence that the present 128-layer stage automatically becomes 64 layers. [3: Phase-tolerant oracle synthesis](https://arxiv.org/abs/2110.07545)

Qrisp exposes phase-tolerant methods and automatic uncomputation. It can serve as an independent implementation comparison, but its native metrics, width allocation, and measurement-assisted options must be audited before using its output here. Installing a different framework is not itself a synthesis strategy. [4: Qrisp MCX documentation](https://qrisp.eu/reference/Primitives/generated/qrisp.mcx.html)

### Conditionally clean ancillas and unary iteration

Khattar and Gidney distinguish a borrowed wire known to have a value under an explicit branch condition from an arbitrary dirty wire. Their revised paper provides MCX, arithmetic, and unary-iteration constructions, including a skew-tree traversal without measurement-based uncomputation. Published Toffoli counts still need conversion to this challenge's gate basis and schedule. [5: Conditionally clean constructions](https://arxiv.org/html/2407.17966v2)

The local `src/mcz.py` already imports the one- and two-clean/dirty KG24 MCX constructions. Recommending “try the new MCX decomposition” therefore repeats existing work. The less explored transfer is the branch invariant and traversal structure at the level of several shared predicates. The current `qrom_tree.emit` consumes a `free` list as clean scratch; offering live outputs through that same interface is not a conditionally clean implementation. Its failed cross-bank variants are evidence of that semantic mismatch, not a rejection of the paper's technique.

### Relative phase and temporary products

Amy and Ross study both unitary relative-phase constructions and measurement-assisted termination. The former is relevant; the latter cannot be imported directly into a standalone U3/CX unitary. In a valid computation `C` that maps basis states to basis states up to phase, a diagonal operation between `C` and its exact inverse cancels those computation phases. That argument must apply to the complete intervening operation, including changes to borrowed controls. [6: Phase/state duality](https://arxiv.org/abs/2105.13410)

This workspace already tested several temporary-product formulations. The remaining opportunity is not merely replacing CCX with RCCX. It is finding a different complete schedule whose phases and temporary-state invariants are correct by construction.

### Partial-specification circuit synthesis

Synthetiq accepts partial operator specifications and finite gate sets, including relative-phase operators and clean-ancilla behavior. Its search uses simulated annealing rather than offering a global optimality certificate. This makes it a concrete candidate for small kernels with unreachable input combinations or allowed internal phases. Its public repository includes OpenQASM examples. [7: Synthetiq](https://files.sri.inf.ethz.ch/website/papers/paradis2024synthetiq.pdf)

The proposed use is a four- to six-wire kernel, not an unconstrained 18-qubit matrix search. A mask must constrain all reachable input columns and forbid leakage from them. Candidate circuits should then be scored after U3/CX conversion and inserted into the full oracle. This directly targets a gap between the repository's minimum-AND searches and the actual quantum objective.

### QROM space/depth tradeoffs and recent Boolean-oracle bounds

Zhu, Sundaram, and Low's unified lookup architecture organizes QROM, SELECT-SWAP, and related space/depth tradeoffs. The extra memory and routing resources are part of the cost; a small asymptotic query depth cannot be borrowed while omitting those wires. With only six clean ancillas, full multiword duplication is restrictive. This source is most useful for accounting for candidate schedules before implementation. [8: Unified lookup architecture](https://arxiv.org/abs/2406.18030)

Nie and Zi's July 2026 preprint gives nearly optimal asymptotic size/depth/ancilla tradeoffs for families of Boolean oracles. It is relevant recent research, but its hidden constants, ancilla regimes, and family-level statements do not establish depth 150—or a lower bound of 197—for this fixed twelve-bit function. The associated counting lower bounds also specify a finite gate set, whereas the challenge permits parameterized U3 gates. [9: Boolean-oracle bounds](https://arxiv.org/html/2607.28402v1)

### Native Classiq context

Classiq's uncomputation documentation supports expressing compute/apply/uncompute and compiler-controlled cleanup. The repository already contains native synthesis experiments; those results were not competitive. A later keychain failure is documented separately. This review did not retry authentication or assume a new login was needed. Native synthesis remains a backend to measure against a concrete new specification, rather than a reason to repeat the original model. [10: Classiq uncomputation](https://docs.classiq.io/qmod-reference/language-reference/uncomputation)

## New exact structural checks

The reproducible diagnostic is `src/research_structure_audit.py`, with output in `artifacts/research_structure_audit.json`. It evaluates the authoritative mask exactly and does not generate a quantum candidate.

### Three bits need side information

There are 11 distinct rows and 11 distinct columns; the GF(2) matrix rank is 10. If `f(x,y)=G(x,h(y))` and **all** y-dependence passes through h, h must distinguish the 11 rows. Consequently it needs at least four classical bits. A three-bit complete row code is impossible in that architecture.

However, if the original `y5` remains available to the decoder, the two halves have **seven and six** row classes respectively. Three additional bits can distinguish the rows within each half. Thus `f(x,y)=G(x,y5,h(y))` is information-theoretically possible with a three-bit code. This does not establish a cheap loader or decoder; it identifies the side information missing from the older “three features” proposal.

There is a stronger test for the tempting five-input loader. Suppose `z=y[0:5]` and the same code h(z) must work in both halves, so `f=G(x,y5,h(z))`. Each z must distinguish the ordered pair of row patterns `(f(·,z), f(·,z+32))`. The audit finds **18 distinct pairs**. Such a shared code needs at least five bits, ruling out the proposed three-output five-input loader in this precise model. Other ordinary-bit selectors have 16–19 ordered row-pair classes; none supports three bits either.

This result does not exclude mixed x/y features, context-dependent transformations, multiple rounds, or a nonclassical intermediate encoding. Those are different models and incur their own costs.

### An exact smaller core plus boundary correction

Define `g(x,y)=f(x & ~1,y)` and `e=f XOR g`. Then g is independent of x0, and e has only **45 marked pixels**. The exact identity is a possible route around an argument that no input bit can be removed without correction.

Unfortunately g and e each have GF(2) rank 9. A small pixel count therefore does not make the correction a cheap rank-factor circuit. Removing y0 similarly leaves 77 correction pixels. A majority core constant on every 2×2 cell leaves 105 correction pixels and a rank-19 residual. These results support only a bounded correction-cost pilot, not a claim of a shallow oracle.

### Scope of the Walsh obstruction

The existing odd-population argument is useful: for nonconstant Walsh characters, every numerator in the transform of f is odd because 1,097 is odd. Adding even integer phase lifts cannot turn those numerators into zero. This blocks the hoped-for sparse ordinary parity expansion of the complete phase function.

It does **not** prove that ancillas are mathematically necessary for all circuits implementing the oracle. General ancilla-free circuits may use non-diagonal intermediate operations. The correct conclusion is that the specific direct CNOT/diagonal-phase representation is expensive, not that every ancilla-free U3/CX implementation has been excluded.

## Recommended next experiments

The research priority is a new shared primitive. The following order makes progress measurable before another large search is launched.

| Priority | Experiment | Evidence required before expanding |
|---|---|---|
| 1 | Context-aware synthesis of a small shared phase/predicate kernel | Explicit reachable-state specification; exact restoration; improvement after full U3/CX integration |
| 2 | Guarded, conditionally clean traversal for a selected cofactor cluster | Proven branch invariant; both active and inactive branches tested; measured compute/phase/uncompute cost |
| 3 | Three-bit row code with retained y5 | Joint loader/decoder design and six-wire lifetime schedule; no assumption that the loader has only five inputs |
| 4 | x0-independent core with exact boundary correction | Compile the rank-9 residual first; stop if its cost consumes the available savings |

For priority 1, choose a small cone around the disk guard/comparison or a repeated cofactor operation, rather than a long generic UCR window. Specify the action on all reachable states, including correlated feature combinations. Allow internal relative phases only where the surrounding sandwich proves cancellation. Search several short circuits using the actual available gates or a finite subset, then compare the complete exported candidates. A local CX win that increases the full critical path is not an improvement. A comparator-only improvement cannot bridge the gap while three full UCR sweeps remain: small-kernel synthesis is a capability test for a new shared loading/phase architecture, not a claim that local cleanup will reach rank 1.

For priority 2, represent a scratch promise explicitly, such as `guard=1 implies w=0`, together with the operations allowed to alter guard and w. Do not pass this wire to an ordinary clean-scratch emitter. The inactive branch must also be restored and must not gain an input-dependent phase. Shared branch prefixes should be retained across several actions so their construction cost is amortized; otherwise this becomes the already-failed independent-cube method again.

For priority 3, optimize code assignment, phase decoder, and workspace together. The three-bit code can free three ancillas, but duplicating or Shannon-splitting it consumes those same wires. Include selection, delta cleanup, and inverse loading before estimating savings. Three 64-layer sweeps already total 192 layers before overhead, so even that attractive sketch has very little margin against 197 and cannot explain a sub-150 claim by itself.

Before any extended search, set two separate milestones: first a verified full circuit below 524, then a credible full schedule below 197. The first is useful evidence but not evidence that the second is close. Preserve all successful artifacts under new names and run `src/exhaustive_verify.py` against each proposed best, with matching hashes. Every reusable-subcircuit transpilation must retain `qubits_initially_zero=False`.

Do not reopen generic seed search, independent rank-basis mutation, direct global Walsh synthesis, ordinary full-BDD materialization, or another naive threshold-cube expansion without a specific new primitive that changes the measured cost. Their negative results are extensive. They are empirical exclusions of implementations, not universal impossibility proofs.

## Search coverage and limitations

Searches covered the exact challenge name, logo/oracle descriptions, the 197-depth score and named leader, public GitHub/QASM references, official challenge information, UCR synthesis, phase-tolerant truth-table loading, relative-phase temporary products, conditionally clean workspace, QROM tradeoffs, partial-specification synthesis, and recent Boolean-oracle bounds. The result set contained challenge announcements and several unrelated older Classiq competitions, but no accessible implementation of the current leading entry.

This is broad public-source research, not a claim to have searched every internet page or private community channel. No private participant solution was accessed. No new complete circuit, upload, ranking improvement, or background search is claimed by this review.

## Sources

1. Classiq. [Quantum Circuit Challenge](https://www.classiq.io/challenge#leaderboard). Live page inspected in Safari, September 9, 2026; scoring, schedule, and leaderboard.
2. Ville Bergholm, Juha J. Vartiainen, Mikko Möttönen, Martti M. Salomaa. [Quantum circuits with uniformly controlled one-qubit gates](https://arxiv.org/abs/quant-ph/0410066). 2004 preprint / 2005 publication.
3. Raphael Seidel et al. [Automatic Generation of Grover Quantum Oracles for Arbitrary Data Structures](https://arxiv.org/abs/2110.07545), section IV.D of the accessible preprint; [published version](https://doi.org/10.1088/2058-9565/acaf9d), 2023.
4. Qrisp. [MCX methods](https://qrisp.eu/reference/Primitives/generated/qrisp.mcx.html) and [Uncomputation](https://www.qrisp.eu/reference/Core/Uncomputation.html). Official documentation, accessed September 9, 2026.
5. Tanuj Khattar and Craig Gidney. [Rise of conditionally clean ancillae for efficient quantum circuit constructions](https://arxiv.org/html/2407.17966v2). Revised May 20, 2025; sections 3–7, especially the measurement-free skew-tree construction.
6. Matthew Amy and Neil J. Ross. [The phase/state duality in reversible circuit design](https://arxiv.org/abs/2105.13410). 2021; [published paper](https://doi.org/10.1103/PhysRevA.104.052602).
7. [Synthetiq: Fast and Versatile Quantum Circuit Synthesis](https://files.sri.inf.ethz.ch/website/papers/paradis2024synthetiq.pdf). 2024, especially section 5; [author-maintained implementation](https://github.com/eth-sri/synthetiq).
8. Shuchen Zhu, Aarthi Sundaram, Guang Hao Low. [Unified Architecture for Quantum Lookup Tables](https://arxiv.org/abs/2406.18030). 2024 preprint / [2025 publication](https://doi.org/10.1103/d896-mktn).
9. Junhong Nie and Wei Zi. [Nearly optimal quantum circuits for Boolean oracles](https://arxiv.org/html/2607.28402v1). July 30, 2026 preprint.
10. Classiq. [Uncomputation](https://docs.classiq.io/qmod-reference/language-reference/uncomputation). Official Qmod documentation, accessed September 9, 2026.

Local evidence: `classiq-challenge-baseline (1).ipynb`; `docs/HANDOFF.md`; `docs/EXPERIMENTS.md`; `docs/CURRENT_DESIGN.md`; `docs/REASSESSMENT_2026-09-09.md`; sources named above; protected `artifacts/524/` QASM and reports; new `artifacts/research_structure_audit.json`. All measurements not attributed to a paper or leaderboard are local evidence or explicitly labeled analytical deductions.
