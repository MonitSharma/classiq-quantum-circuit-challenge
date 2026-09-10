# Phase-aware dynamic six-ancilla compiler

## Question

Can the rank-10 logo phase be compiled more shallowly by expanding each
rank-factor product into phase edges, computing only the nonlinear XAG nodes
needed for an edge, and using `q12..q17` as one shared pool of six clean
ancillas?

## Implementation

`src/phase_pebble_rank.py` uses the bounded, truth-table-verified low-AND XAG
cache when available. For roots

```
a = XOR(X_j),   b = XOR(Y_k)
```

it forms the GF(2)-cancelled edge set `(X_j, Y_k)`, including affine and
constant constituents. Each edge is scheduled independently: compute the
required nonlinear ancestors, emit the diagonal phase, and reverse the exact
toggle path. The planner enforces a single six-ancilla pool and tracks peak
live values. Phase-edge algebra was checked over all 4096 x/y assignments for
every reported pair.

All scoring transpilation uses `qubits_initially_zero=False` and the exact
`u3`/`cx` basis.

## Pair results

All 30 combinations across `pair_terms`, `rank_terms`, and
`rank_mc_pareto_terms` were attempted. Every row was feasible under the
dynamic six-ancilla scheduler. The machine-readable results are in
`artifacts/phase_pebble_pair_metrics.json`; the 30-row execution log is in
`artifacts/phase_pebble_progress.jsonl`.

| basis | feasible | sum depth | sum CX | largest pair depth |
|---|---:|---:|---:|---:|
| `pair_terms` | 10/10 | 3401 | 3721 | 1042 |
| `rank_terms` | 10/10 | 3882 | 4267 | 1042 |
| `rank_mc_pareto_terms` | 10/10 | 3225 | 3320 | 728 |

The `rank_mc_pareto_terms` rows use the bounded XAG cache except for the one
factor whose bounded solver remained unresolved; that row is explicitly
labelled `formula_fallback`.

## Complete-oracle result

The ten `rank_mc_pareto_terms` pair circuits were composed and serialized as
`artifacts/phase_pebble_rank_mc.qasm`:

| metric | result |
|---|---:|
| depth | 3163 |
| CX | 3318 |
| width | 18 |
| basis inputs checked | 4096 |
| ancilla error | `3.72e-15` |

The exact verifier report is `artifacts/phase_pebble_rank_mc.exhaustive.json`
and records SHA-256
`a0a57e782d707b64d4c5c667445582fc5efa85c76651f986bd028a808eb9bd30`.

## Conclusion and next path

The experiment answers the feasibility question positively: dynamic pooling
makes all tested pair schedules feasible, including pairs that failed the
fixed 3+3 side allocation. It does not improve the complete oracle because
independent per-edge recomputation dominates the cost. The next required
step is cross-edge retention: keep a nonlinear XAG node live across adjacent
edges and search edge order, retention, and recomputation jointly under six
ancillas. A second priority is a multi-output XAG exposing shared predicates;
scalar low-AND quality is not enough.

This candidate does not beat the protected depth-531 circuit and must not be
treated as a new best.
