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
