# Complete-schedule non-monotone pilot

The repository audit found no implementation combining all required features:
18 writable wires, exact 4096-input semantics, arbitrary interior mutation of
an existing fixed-length schedule, cached suffix replay, and the final
affine-span logo objective. `sub140_projection_anneal.py` is fixed-length but
is a 9-wire/64-input class-separation search that recomputes each trial.
`destructive_semantic_search.py` is exact and 18-wire but prefix-growing.

`src/post190_whole_schedule.py` now supplies the missing Python reference
engine. It stores complete macro-layer schedules, caches all boundary states,
and replays only the changed suffix after a mutation. The semantic primitives
are directly the validated destructive engine’s CX/RCCX implementations and
the score separates exact affine-span membership from the order-2 proxy.
Mutation families include whole-layer rewrites, single-gate rewires,
interior block ruin/recreate, layer relocation, and uphill Metropolis accepts.

The initial pilot is deliberately bounded and is not an oracle search result.
The 3-second pilot completed 3,000 mutations from a seven-stage random
schedule, accepted 1 uphill move, accepted 894 early-half mutations, and
performed 1,338 block rewrites. Its best order-2 proxy residual was 827 at
the pilot's random schedule depth; no exact affine-span solution was found.
The protected
`artifacts/190/two_stage_190.qasm` artifact remains immutable.

Cached suffix replay was measured against full replay on 500 mutations at each
location: approximately 566x faster at the beginning, 1,459x in the middle,
and 2,771x at the end (about 222 full versus 126k–615k cached evaluations per
second). Randomized bit-for-bit replay tests passed, including interior
mutations and unchanged rejected state.

The current destructive artifact scan found a shallow historical Pareto point
at approximately depth 98 / proxy residual 501 in
`artifacts/destructive_semantic/combo_seed20260926_b32x8_p8.json`; this pilot
did not dominate it. No full-logo pilot portfolio was launched after the short
engine/control run.

Reproduce the correctness controls and pilot with:

```sh
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_post190_whole_schedule.py
PYTHONPATH=src .venv/bin/python src/post190_whole_schedule.py --outdir artifacts/post190_whole_schedule --seconds 10 --iterations 10000 --seed 0
```
