# Multiplicative-depth campaign

## Objective

This campaign is separate from the protected 524-depth oracle work. It asks
whether the exact logo has a shallow XOR--AND graph (XAG) when sequential
nonlinear layers are optimized before reversible or quantum lowering.

An affine XOR combination is free for this structural metric. For an AND node
`g = a AND b`,

```text
MD(g) = 1 + max(MD(a), MD(b)).
```

AND count and multiplicative depth are therefore different objectives. A
large, shallow graph may be more useful than a compact but deeply sequential
one.

## Exact target

The authoritative predicate is `src/search.py::logo`, with little-endian
`x = q[0:6]` and `y = q[6:12]`. The independent evaluator in
`src/md_xag.py` uses 4096 truth-table points and constant-one signal 0.

| Property | Value |
|---|---:|
| Variables | 12 |
| Truth-table points | 4096 |
| Marked points | 1097 |
| Algebraic degree | 12 |
| Nonconstant ANF terms | 886 |
| Truth-table SHA-256 (little-endian bytes) | `d86d44aa45393ecc14ddfed0ed08d97e550a2786d58f61173fa71a6394253cf1` |

The deterministic truth table is exported at
`artifacts/multiplicative_depth/logo_truth.hex`. The independent evaluator and
its tests do not trust a compiler's correctness report.

## Existing exact XAG audit

The audit is saved at
`artifacts/multiplicative_depth/existing_xag_audit.json`.

| Network | Exact | ANDs | MD | ANDs per MD layer | Live-width estimate |
|---|---:|---:|---:|---:|---:|
| Balanced ANF monomials | yes | 5096 | 4 | 2767, 1390, 812, 127 | 892 |
| Shared rank-factor formula XAG | yes | 97 | 6 | 29, 21, 20, 14, 10, 3 | 22 |

The balanced ANF network is an explicit MD=4 upper bound, but its enormous
layer and live widths make it unsuitable for six-ancilla quantum realization.
The shared rank-factor formula graph is much smaller and reaches MD=6. Its
corrected topological last-use schedule has estimated nonlinear live width 22;
this is promising structurally, but it is not yet a quantum candidate.

The shared XAG was independently reconstructed from the repository's formula
graph and verified by `md_xag.XAG.evaluate()` over all 4096 points. The
existing shared-XAG phase pilot is separately recorded in
`docs/PHASE_HISTORY.md`; its reversible pebbling cost must not be confused
with the graph's multiplicative depth.

## Current conclusion

**Conditional GO for structural optimization.** The exact logo demonstrably
has shallow nonlinear structure (MD 6 with 97 ANDs, and a trivial MD 4
construction with large width). The next required work is depth-oriented XAG
rewriting, controlled size growth, affine-basis search, and live-width-aware
analysis. No QASM lowering should begin until a schedule with materially
smaller nonlinear live width is found.

## Isolated mockturtle pilot

The official mockturtle repository was checked out under
`external/mockturtle/` at commit
`0886ebfdd101ce1110daf3d60b96d72edd3143ea`. The checkout and build output are
ignored so the repository stays small; the source URL, compiler, and exact
build command are recorded in `tools/mockturtle/README.md`.

The standalone pilot in `tools/md_synth/md_synth.cpp` ingests the exact logo
truth table and an exported XAG seed, then runs selected mockturtle pipelines.
It independently checks all 4096 points after each pipeline; the machine-
readable logo results are recorded below.

That ingestion step is now complete. The exact shared-rank seed is exported at
`artifacts/multiplicative_depth/seeds/shared_rank.xag`; the C++ executable
reads both that seed and `logo_truth.hex`. `xag_balance` produced an exact
81-AND, MD-6 result. The apparent MD-4 and MD-5 results from algebraic depth
rewriting were rejected because the independent 4096-point evaluator found
truth-table mismatches. These are negative correctness results, not usable
candidates. Full pipeline outcomes are in
`artifacts/multiplicative_depth/mockturtle_logo_pilot.json`.
Repeating `xag_balance` is an exact fixed point: it remains MD 6 with 81 ANDs
and the same layer widths.

## First structural report

| Quantity | Result |
|---|---:|
| Best exact AND count observed | 81 |
| Best exact multiplicative depth observed | 4 (balanced ANF baseline) |
| Best exact shared-XAG MD | 6 |
| Best exact shared-XAG max layer width | 20 (affine trial 118 after balance) |
| Best exact shared-XAG live-width estimate | 11 after affine substitution and balance |
| Exact mockturtle pipeline | `xag_balance`, MD 6 / 81 ANDs |
| Affine-basis search | 129 exact ANF trials; identity remained best |

The MD-4 result is the large balanced-ANF construction (5096 ANDs), not a
practical low-width candidate. The most useful current exact structure is the
81-AND balanced shared-rank result at MD 6, with an 11-value post-balance
live-width estimate after affine substitution. This is still a **CONDITIONAL GO** for
structural XAG work and not a justification for quantum lowering yet.

The bounded affine screen used seed `20260910` and elementary invertible row
XORs, swaps, and input complements. All 129 transformed ANF constructions were
exact. The identity basis remained best under the required MD, live-width,
layer-width, AND-count ordering: MD 4, 5096 ANDs, and estimated live width
892. This is evidence about the balanced-ANF family only; it does not rule
out a better affine basis for a shared or factored XAG. Results are saved in
`artifacts/multiplicative_depth/affine/anf_basis_search.json`.

A second screen substituted 129 deterministic invertible affine bases directly
into the shared-rank XAG, exported each transformed truth table, and ran the
exact mockturtle balance pipeline. All 129 source and post-balance networks
passed exhaustive checking. Trial 118 is the current width Pareto point: MD 6,
81 ANDs, and layer widths `[20, 20, 15, 13, 10, 3]` (post-balance live-width
estimate 11).
Its affine basis has 45 CNOT-like row-XOR operations plus five input
complements as a simple preprocessing estimate. Results are in
`artifacts/multiplicative_depth/affine/shared_rank_search.json`.

## Quantum feasibility gate

The best exact candidate now passes the structural MD-6 milestone, so a
resource pre-analysis is recorded in
`artifacts/multiplicative_depth/quantum_feasibility.json`. Its post-balance
live-width estimate is 11 versus six clean ancillas, leaving a workspace gap of
five nonlinear values. Therefore no QASM lowering has started. The next valid
step is a destructive/recomputation or phase-history schedule that explicitly
closes this gap; an abstract MD number alone is not sufficient.

That schedule experiment is now complete for the exact pre-balance affine
seed. `src/pebble_md.py` streams the ten output signals as phase taps and
clears the dependency cone after each tap. The exact bounded result in
`artifacts/multiplicative_depth/quantum_pebble_feasibility.json` reaches peak
live width 6 with 304 nonlinear toggles and returns to an empty live set.
This is a structural feasibility result; it does not yet account for affine
wire synthesis, RCCX relative phases, or serialized U3/CX depth.

## First quantum prototype

The first phase-history lowering of the exact streamed rank seed is
`artifacts/multiplicative_depth/md_rank_stream.qasm`. It uses 18 qubits and was
exhaustively checked over all 4096 inputs with zero meaningful ancilla leakage.
The serialized `u3`/`cx` result is depth 1046 with 903 CX and SHA-256
`75fe5e9fa42e4496a6cb8036712b42008885bab87202d8110f48ce67682ddc5c`.
This is well above the requested `<350` first-prototype diagnostic threshold,
so it is a negative scheduling result, not a competitive submission. The
structural XAG remains promising; the next work must reduce affine transition
and recomputation costs before any broad quantum search.

The affine trial-118 prototype is also exact but worse: explicit reversible
basis preparation and cleanup produce depth 2593, 2716 CX, and QASM SHA-256
`5875ec5d9a813128c39d126eb7ce3c0449dcb261371ae1050c18a6f6dfe4b4fd`.
This separates a useful classical affine basis from a useful quantum basis;
the affine transform cannot simply be added as a 50-operation preprocessing
step under the current lowering.

A bounded pytket `FullPeepholeOptimise` diagnostic reduces the original
streamed prototype to depth 1031 with the same 903 CX. Its standalone QASM was
also exhaustively verified; SHA-256 is
`436613fe2ce1ecf74a7b10eac00188237e7e656a3dc860d8c5a6adf53737038d`. This is
useful cleanup evidence but remains far above the `<350` diagnostic target.

Reproducing the best documented phase-tap order
`[5, 2, 0, 9, 7, 3, 8, 4, 1, 6]` gives an exact depth-1035 / 899-CX stream;
pytket cleanup lowers it further to depth 1023 / 899 CX. The matching QASM SHA
is `b1b126b5077824084304b79fcf4ff6c683b3e99023eaae261c98f6247a46b313`.
This is the current best quantum artifact in this campaign, but remains a
negative result against the requested competitive range.

The balanced 81-AND network is exported back into the independent XAG format
at `artifacts/multiplicative_depth/optimized/affine_balance_118.xag` and passes
independent exact evaluation. Its direct affine phase-tap lowering was also
exhaustively verified, but scored depth 2742 / 2810 CX with SHA-256
`684807b50fa521d0615568620d561b266fc25ccb8f3946bce8e4fc4f9cffbe12`.
This is a decisive caution: lower XAG AND count and equal MD do not imply a
better quantum schedule; affine fan-in and output-cone sharing must be part of
the optimization objective.

Balancing in the original input basis and lowering its 81-AND graph without a
basis-change sandwich was also exhaustively verified, at depth 1194 / 1016 CX
with SHA-256
`3232ebeb0ccf2928fe1d2d18c0c5f420afff1a7418e6ccaf1d25e994673cce86`.
The original 97-AND two-form CZ stream remains the best tested realization.

A direct final-signal-to-ancilla phase-tap variant was also exhaustively
verified, but scored depth 1207 / 1003 CX with SHA-256
`06e5a7a56211aeb41cd0950235d0430367eb91f42fb2b03d08dd0959b1fbafb6`. The
existing two-form CZ phase lowering at 1046 / 903 remains preferable; direct
signal taps do not by themselves solve the transition-cost problem.

## Reproducibility

```bash
PYTHONPATH=src .venv/bin/python src/md_xag.py \
  --out artifacts/multiplicative_depth/anf_balanced_baseline.json \
  --truth-hex artifacts/multiplicative_depth/logo_truth.hex
PYTHONPATH=src .venv/bin/python src/audit_multiplicative_depth.py
PYTHONPATH=src .venv/bin/python src/export_md_seed.py
PYTHONPATH=src .venv/bin/python src/verify_md_seed.py \
  artifacts/multiplicative_depth/optimized/affine_balance_118.xag \
  artifacts/multiplicative_depth/affine/shared_rank/seed_118.hex
./tools/mockturtle/build/md_synth \
  artifacts/multiplicative_depth/logo_truth.hex \
  artifacts/multiplicative_depth/seeds/shared_rank.xag balance
PYTHONPATH=src .venv/bin/python src/pebble_md.py
PYTHONPATH=src .venv/bin/python src/md_optimizer_diagnostic.py
PYTHONPATH=src .venv/bin/python src/md_ordered_quantum.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```
