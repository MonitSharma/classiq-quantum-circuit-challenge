# Scalar closure and global endpoint experiment

This run was performed on current `main`. The protected 531-depth QASM
was not modified. All complete candidates below use serialized `u3`/`cx`
QASM, width 18, and `qubits_initially_zero=False` during scoring.

## Results

The best verified rank-family result is now
`artifacts/753/pair_boundary_753.qasm`: **depth 753 / 742 CX / width 18**.
It is the existing `pair_terms` pair compiler with a local-search order
`[9,7,1,2,5,4,8,0,6,3]`. Exhaustive verification checked all 4096 inputs,
with zero ancilla leakage; QASM SHA-256 is
`df0be59c2b41a2b5138578bdc321555fea46a13628289429198ee0b2c2992a89`.

The protected overall best remains `artifacts/531/full_mux_531.qasm` at
531 / 1020 / 18, SHA
`8f7e2617cf1435ea76cc70688544b4b0e3a8b5082d82293f98777d90d5a3fda6`.

Current all-pair baselines, freshly compiled from the three stored bases, are:

| basis | depth | CX |
|---|---:|---:|
| `pair_terms` | 779 | 736 |
| `rank_terms` | 842 | 781 |
| `rank_mc_pareto_terms` | 859 | 800 |

The older 795/754 and 803/751 values are therefore historical measurements,
not reproducible current baselines under this invocation.

The basis-matched portfolio closure tested 12/64 substitutions for
`pair_terms`, 11/54 for `rank_terms`, and 13/75 for
`rank_mc_pareto_terms` (one-term/two-term counts). The best substitution was
775 / 749 on `pair_terms`; the best two-term Pareto substitution was 853 / 795.
Neither beat the boundary-ordered result. A 50-order control was also
included for each basis.

The local-order neighborhood evaluated 855 unique permutations and improved
756 to 753. All 720 ordered triples were measured for second-order context;
its greedy rollout scored 775/744 and did not improve the local-search result.
For the 753 order, raw high-level global compilation scored 755/742, versus
753/742 for independently lowered blocks, so raw composition did not help.

Six-variant exposure retained six variants for eight terms, two for term 5,
and three for term 9. Joint variant/order local search evaluated 468 states and
scored 755/735. The K=4 variant boundary DP evaluated 18,944 states; its best
actual candidate scored 756/734. No non-isolated-optimal variant improved the
verified 753-depth result.

## Global 12-edge identity

Extraction produced 12 surviving phase edges, 11 unique x endpoint functions,
and 11 unique y endpoint functions. The exact endpoint pairs are stored in
`artifacts/global_12_edge_endpoints.json`; each row contains 64-bit integer
truth tables and source-node provenance. The direct identity check covered all
4096 `(x,y)` inputs and found zero mismatches.

Endpoint truth-table pairs, in edge order, are:

| edge | x truth table | y truth table |
|---:|---:|---:|
| 0 | 134217724 | 17329834319396470784 |
| 1 | 134217724 | 17311836971370283008 |
| 2 | 132199093370880 | 134219776 |
| 3 | 281479271677952 | 4063232 |
| 4 | 140746078289920 | 251688960 |
| 5 | 281466386776064 | 268433408 |
| 6 | 2025493932409880576 | 123626338648064 |
| 7 | 3689348814741910320 | 17042430230528 |
| 8 | 922337203685477580 | 17042430230528 |
| 9 | 1154047404513689600 | 70437463654400 |
| 10 | 279223176896970752 | 264398186741760 |
| 11 | 105604655874048 | 67112960 |

The endpoint inventory reports 9/11 x functions and 9/11 y functions present
in the existing bounded min-AND cache. Endpoint degrees are 5 or 6; the full
inventory is in `artifacts/global_endpoint_inventory.json`.

Compiling the 12 edges independently with `pair_circuit` produced a verified
**819 / 773 / 18** candidate. This is a substantial improvement over the
1591-depth formula-graph probe, but it does not beat 756 or 531.

The endpoint interaction matrix has GF(2) rank **10**. Its derived rank-10
factorization is exactly reconstructed over all 4096 inputs and compiled to a
verified **854 / 789 / 18** candidate. The factorization therefore did not
improve the direct 12-edge construction.

Selective star merges were negative: shared-x scored 832/785, shared-y
834/822, and both stars 852/797, versus 819/773 without merging. Simple
critical-path accounting shows the 753 circuit is dominated by ancilla wires
q16/q15/q14/q13/q17/q12, with 366/313/210/204/195/181 touched operations.

## Decision

The cheap scalar neighborhood is not completely useless: ordering alone found
a verified 753-depth improvement. However, scalar block substitution remains
far from 531 and cannot plausibly approach the leaderboard's approximately
291-depth range.

The 12-edge representation is mathematically sound and materially better than
its original implementation, but independently recompiling its endpoints is
still not competitive. The data justifies a future joint endpoint compiler,
especially because the endpoint inventory is not identical to the old scalar
factor inventory. The next serious architecture should jointly synthesize and
schedule the endpoint functions with shared nonlinear nodes and dirty-ancilla
lifetime management. Do not claim that vector-XAG or affine-frame optimization
has already been implemented.

## Persistent parity-frame pilot

The new `persistent_parity.py` core represents arbitrary 18-wire affine frames,
extracts CX/X circuits into frames, synthesizes general GF(2) transitions, and
passes exhaustive transition tests. A diagnostic on pair terms 5, 9, 4, and 2
shows linear-preparation transition sums of 29/24, 16/8, 11/0, and 15/8
(depth/CX), versus old prepare/restore accounting of 36/26, 22/8, 16/0, and
18/8. This confirms a real linear-frame opportunity, particularly for terms 5
and 9. It is not yet an end-to-end nonlinear oracle compiler: RCCX changes the
semantic signal basis, so live nonlinear signals still need to be represented
in the frame state before a persistent candidate can be accepted.

The span-aware hybrid fallback was then attempted on all four pilot terms. All
four were rejected as `infeasible_prototype` with the same frame-span failure;
there is no accepted persistent pair QASM or end-to-end depth claim. The
negative result is useful: preserving only total affine rank is insufficient,
and canonical fallback must retain the full input/live semantic span through
every nonlinear uncompute.

A truth-table-backed semantic-frame prototype was also attempted. Its general
transition core passes random exact tests on 18-dimensional function spans,
but the first end-to-end pair construction failed to preserve a live nonlinear
signal through a frame transition. This is recorded as an implementation
blocker, not as a circuit result; the next version must make live-node rebinding
part of the transition invariant.

The next semantic-frame revision fixed two implementation issues: live-node
wires are now excluded from temporary allocation, and every transition requires
exact (not merely FULL-quotiented) control and target truth tables before RCCX.
Three of four pilot pair paths now compile as internally consistent phase
components (terms 5, 9, and 2 at 449/605, 415/491, and 67/49 depth/CX,
respectively). They are not standalone logo oracles and are not a new verified
submission; exhaustive logo verification correctly rejects each component.
The clean-ancilla allocation invariant then fixed the term-4 failure. All four
pilot components now pass exhaustive verification against their individual
pair masks, with metrics 137/102, 455/612, 463/540, and 95/96 depth/CX for
terms 4, 5, 9, and 2. These are verified phase components, not standalone
logo oracles. A direct composition using the inventory's independent block
variants measured 1439 depth / 1704 CX, so the components cannot simply be
spliced into the 753 construction; its boundary-optimized variants and
cross-block scheduling must be rebuilt jointly. A clean-ancilla register
assignment search then found a verified depth improvement without changing
the Boolean decomposition: independently permuting q12--q17 at each pair
boundary reduced the fixed-order oracle from 753/742 to **739/743** depth/CX
(width 18). A deterministic single-swap descent from that assignment then
reached **732/729** depth/CX. The candidate is
`artifacts/732/ancilla_assignment_732.qasm`; exhaustive verification covers
all 4096 basis inputs with zero ancilla leakage. This is now the verified
rank-family best, while the 531/1020/18 circuit remains the overall depth
record in the repository. The next target remains shared persistent frames
or a joint compiler that can reduce serialization below 732.

As a bounded post-pass, pytket `CliffordSimp` applied to the exact 732 QASM
reduced the serialized depth further to **718/729** depth/CX without changing
width. The exact U3/CX output in `artifacts/718/tket_ancilla_assignment_718.qasm`
passes exhaustive verification on all 4096 inputs with zero ancilla leakage.
`FullPeepholeOptimise` reached 719/729; a second pass composition did not
improve 718. This is a verified compiler result, not a new Boolean
decomposition; the overall 531/1020/18 circuit remains shallower.

Post-732 assignment diagnostics found no further improvement in 1,200
coordinated two-/three-block mutations, 1,200 independent random restarts,
or a focused 500-trial search on the most influential adjacent boundary.
The verified circuit's largest wire occupancies are q14=328, q12=263,
q16=255, q13=251, q17=179, and q15=168 touches; final wire completion
spans layers 718--731. This indicates a distributed dependency chain rather
than one removable hot-wire tail, strengthening the case for changing the
nonlinear schedule itself.

The time-limited semantic XAG model-bank pilot enumerated one model at k and
one at k+1 for 12 representative functions, independently verified every
returned model, and found zero predicates reused across different outputs.
This is a bounded negative pilot only; the initial run covered 12 functions.

The resumable bank has since covered all 28 unique pair/endpoint functions
present after deduplication. The k/k+1 queries returned UNKNOWN for many
functions under the short timeout, so only successfully returned models were
eligible for union selection. Among those models, pair-x, pair-y, endpoint-x,
and endpoint-y each showed 0% semantic union saving. This is evidence against
easy sharing in the sampled model space, not a proof against a longer-timeout
joint XAG search.

A true shared-XAG persistent compiler was then implemented in
`src/persistent_global.py`. It retains nonlinear nodes across term boundaries,
uses exact semantic-frame transitions, and enforces all 12 input values plus
live-node values and clean unused ancillas. The fixed order produced a fully
verified oracle at **1838 depth / 1524 CX / width 18**, with zero ancilla
leakage over all 4096 inputs. This is substantially worse than the 718/729
register-assignment result: persistent transitions are currently more
expensive than the saved recomputation. The result is a valid negative
architecture measurement, not a submission candidate.

## Classiq model-only boundary

The native Classiq model generator was exercised locally for
`rank_formula_whole` with text-only mode enabled. Native synthesis was not
run: it would upload the QMOD to the external Classiq service, and that upload
was explicitly declined. Therefore this experiment produced no new circuit
depth, CX, or width result and must not be interpreted as a synthesis result.
No QMOD was uploaded to Classiq in this iteration.

Generated artifacts:

- `src/extract_global_endpoints.py`
- `src/global_endpoint_pair_oracle.py`
- `src/global_endpoint_matrix.py`
- `src/global_endpoint_inventory.py`
- `src/global_endpoint_rank_oracle.py`
- `src/anchored_rank_search.py`
- `src/rank_boundary_search.py`
- `src/pair_756_local_search.py`
- `src/pair_triple_boundary_search.py`
- `src/pair_raw_global_comparison.py`
- `src/global_endpoint_star_search.py`
- `src/current_critical_path.py`
- `src/pair_variants.py`
- `src/pair_variant_joint_search.py`
- `src/pair_variant_boundary_dp.py`
- `src/persistent_parity.py`
- `src/persistent_parity_pilot.py`
- `src/semantic_frame.py`
- `src/xag_model_bank.py`
- `artifacts/global_12_edge_endpoints.json`
- `artifacts/global_12_edge_identity_check.json`
- `artifacts/global_endpoint_inventory.json`
- `artifacts/global_endpoint_matrix.json`
- `artifacts/global_endpoint_rank_terms.json`
- `artifacts/global_endpoint_pair_best.qasm`
- `artifacts/global_endpoint_rank_best.qasm`
- `artifacts/756/pair_boundary_756.qasm`
- `artifacts/753/pair_boundary_753.qasm`
- `artifacts/pair_variant_inventory.json`
- `artifacts/pair_variant_dp_search.json`
- `artifacts/pair_variant_boundary_costs.json`
- `artifacts/persistent_parity_pilot.json`
- `src/persistent_pair.py`
- `artifacts/persistent_pair_pilot.json`
- `artifacts/persistent_pair_2.qasm`
- `artifacts/persistent_pair_4.qasm`
- `artifacts/persistent_pair_5.qasm`
- `artifacts/persistent_pair_9.qasm`
- `src/ancilla_assignment_search.py`
- `artifacts/739/ancilla_assignment_739.qasm`
- `src/ancilla_assignment_descent.py`
- `artifacts/732/ancilla_assignment_732.qasm`
- `src/persistent_global.py`
- `artifacts/persistent_global.qasm`
- `artifacts/persistent_global.exhaustive.json`
- `src/tket_global_optimize.py`
- `artifacts/718/tket_ancilla_assignment_718.qasm`
