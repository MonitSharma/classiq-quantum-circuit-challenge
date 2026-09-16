# AND-network route: measured results and corrected scope

Date: September 16, 2026. Protected best: **185 / 854 / 18**.
Read `POST185_DESTRUCTIVE_XAG_IMPLEMENTATION.md` for the latest implementation.
The earlier version of this note is preserved in
`archive/POST185_AND_NETWORK_ROUTE_20260916_superseded.md`; its architectural
identifications and impossibility claims are superseded below.

## Leaderboard evidence

| Entry | Depth | CX | CX / depth |
| --- | ---: | ---: | ---: |
| Rank 1 in supplied screenshot | 137 | 561 | 4.10 |
| Rank 2 | 166 | 348 | 2.10 |
| Rank 3 | 175 | 343 | 1.96 |
| Rank 4 | 175 | 352 | 2.01 |
| Rank 5 | 177 | 736 | 4.16 |
| Protected local circuit | 185 | 854 | 4.62 |

Only348 is divisible by six. The other counts do not identify AND counts or
private circuit architectures. Boolean/Toffoli-heavy circuits are a hypothesis.
A relative-phase CCX compute/inverse pair costs six CX before routing/fusion;
`6G+2R` is a cost proxy, not an architectural fingerprint (it is always even,
whereas561 and343 are odd). No competitor circuit has been reconstructed.

## Existing exact networks

| Network | ANDs | Multiplicative depth | Operand routing proxy | Greedy peak live |
| --- | ---: | ---: | ---: | ---: |
| shared_balance | 81 | 6 | 36 | 15 |
| advanced_round4 | 62 | 8 | 63 | 14 |
| advanced_round2 | 65 | 7 | 56 | 14 |
| advanced_shared_balance | 64 | 9 | 64 | 16 |

The558-CX estimate for shared_balance is close to561, but has not been realized
by a physical compiler at18 wires or137 depth. Independent operand-popcount
routing estimates omit simultaneous control exposure, storage and scheduling.
Logical AND depth does not equal the number of disjoint physical CCX batches.
The files affine_none and affine_balance_118 fail the exact-logo loader check
and are not valid candidates.

## Width is compiler-dependent

The input-preserving clean-node compiler freezes12 coordinate wires and uses
six clean node targets. That restriction does not apply to every allowed circuit.
For example, `x2 ^= x0 & x1` is reversible even though original x2 is no longer
in the affine span of the current wire functions. All18 wires may be temporarily
changed if the final oracle restores the coordinates and clean ancillas.

The following are constructive/heuristic results, not lower bounds:

| Network | Smallest scratch budget found by current planner | Toggles |
| --- | ---: | ---: |
| shared_balance | 11 | 212 |
| advanced_shared_rank | 14 | 240 |
| advanced_round2 | 15 | 224 |
| advanced_shared_balance | 17 | 240 |
| advanced_round4 | 18 | 228 |
| advanced_round3/5/nist_sub45 | 20 | 156–160 |

Width correlates with multiplicative depth in this sample; neither determines
the other. A failed greedy plan is not an exact pebble-number result. The old
5,131-layer root-by-root compiler is not evidence against all XAG implementations.

The212-toggle shared_balance plan is now emitted and quantum-verified on all
4,096 inputs at **23 wires / 692 depth / 728 CX**. It is explicitly width-ineligible.
The new bounded exact six-pebble diagnostic at horizon212 times out; it does
not prove six scratch wires impossible.

The deep-research report's six-target throughput argument is a useful warning
about the literal primitive schedule. Its approximate162-layer estimate assumes
specific primitive/boundary behavior; it is not a universal lower bound after
arbitrary resynthesis. More clean-pebble optimization is not the primary route.

## Measured side-loader outcomes remain useful

`post185_and_loader.py` builds the NIST min-AND encoders: y at256/245 and x at
283/265 depth/CX, versus the existing78/198 rotation loader. Their dense affine
operand preparation dominates. Those particular encoders lose; minimum AND count
alone is not a useful optimization target here. This does not close joint
18-wire destructive encoding.

`post185_width_synthesis.min_degree` is finite annealing. It found best maximum
code degree5, but did not prove a global minimum or degree-three impossibility.
Its cascade search reached residual1–2, not zero; this is also heuristic.
Earlier exact SAT degree results have their own specific raw-tag/model scope.
Neither heuristic establishes that every scratch-free loader is impossible.
These side-loader searches remain low priority, not universally disproved.

## Current target

Lower existing exact whole-logo XAGs onto18 physical wires with destructive
coordinate reuse, paid affine control preparation, intermediate phase taps,
and literal inverse restoration. Allow recomputation and score complete native
depth. Preserve the joint x14+y13 line with corrected storage models.

`destructive_phase_xag.py` is a bounded physical search implementation, not a
complete compiler guaranteed to lower every XAG. Its synthetic dirty-register
positive controls work; the full logo networks have not yet completed. The
initial greedy guard and relaxed variants are documented separately.
