# Hybrid portfolio and affine-frame assessment

## Complete results

The local portfolio was benchmarked on all ten `rank_mc_pareto_terms`. The
portfolio included the existing pair compiler, parallel XAG compiler,
bounded-minMC pair compiler, independent phase-pebble compiler, and retained
phase-pebble compiler. Infeasible implementations were recorded rather than
treated as failures of the whole run.

The best isolated primitive was selected per term and 500 random complete
term-order permutations were compiled. The best complete hybrid is
`artifacts/hybrid_rank_best.qasm` and its affine-stage fallback is
`artifacts/hybrid_affine_rank_best.qasm`:

| candidate | depth | CX | width |
|---|---:|---:|---:|
| hybrid portfolio | **840** | **798** | 18 |
| hybrid + affine-stage fallback | **840** | **798** | 18 |
| protected best | 531 | 1020 | 18 |

The hybrid QASM was exhaustively verified over all 4096 coordinate inputs,
with zero ancilla leakage. Its verification SHA is
`fb881799e506d62590f4351fcee179b5cab3edf3d86e23b507477fa3a7932d30`.

A second 500-trial search varied compiler assignment and term order jointly.
Its best verified result was 1027/1043, so mixed assignment did not improve
the fixed multi-objective portfolio hybrid.

## Retention correction

The beam search now stores true accumulated transition cost `g` separately
from heuristic `h`; beam ranking uses `f = g + h`. Future-use scoring counts
only un-emitted edges and values live nodes by remaining incident edges and
ancestor recomputation cost. Distinct row, column, shared, cheap-transition,
and retention-first policies were measured.

Term 6 reached 194/200 and term 7 reached 202/223 depth/CX across beam widths
64, 256, and 1024. The selected retained complete oracle, after 100 term
orders, was 1818/2070; it remains inferior to the hybrid portfolio.

The corrected global term-6 search over `(live_nodes, emitted_edge_mask)`
completed after 1,295 states, producing 204/188 with 10 compute and 10
uncompute actions. Campaign details are in
`artifacts/retention_search_diagnostics.json`.

## Affine-frame stage

`src/affine_frame.py` implements an exact six-bit affine parity-frame model
with CNOT/X transitions and invertibility checks. `src/phase_retention_affine.py`
benchmarks the fixed retained schedules and records raw CNOT, RCCX, CZ, and X
counts in `artifacts/affine_frame_cost_breakdown.json`. The frame primitive
passes its unit test, but a full frame-aware nonlinear compiler was not
validated; therefore no affine improvement is claimed. The generated
`hybrid_affine_rank_best.qasm` is explicitly the verified portfolio fallback.
The older `artifacts/xag_affine.qasm` was rechecked and failed exhaustive
phase verification, so it is not included in any score or assignment.

## Cross-term and vector-XAG evidence

`artifacts/cross_term_predicate_inventory.json` contains 42 unique cached x
internal predicates and 40 unique cached y predicates, with zero repeats on
either side. That provides no immediate scalar-predicate sharing opportunity.
The explicit vector assessment is in `artifacts/vector_xag_metrics.json`;
scalar sharing savings are zero. A shared formula-derived graph was also
tested and was worse: 46 x nodes versus 42 independently cached nodes, and
45 y nodes versus 40. Vector-XAG synthesis was therefore not started.
This is recorded as a search-limit result, not an impossibility proof.

## Comparison and next experiment

| architecture | depth | CX |
|---|---:|---:|
| pair/Pareto family | ~803 | ~751 |
| independent phase-pebble | 3163 | 3318 |
| retained phase-pebble | 1818 | 2070 |
| hybrid portfolio | **840** | **798** |
| protected best | **531** | **1020** |
| historical leaderboard target | ~291 | — |

The next genuinely different experiment is a joint multi-output XAG search
that optimizes shared nonlinear structure and affine parity transitions
together. The current scalar cache cannot justify cross-term retention by
itself.
