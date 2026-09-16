# Joint 18-wire x14+y13 feasibility pre-screen

Date: 2026-09-16

## Result

**PRESCREEN PASS — exact affine-frame feasibility remains unresolved.**

The saved exact Boolean witnesses were combined into one symbolic 12-input,
18-wire system:

- x witness: `artifacts/post190_nist_variants/x_candidate_0.json`, 14 ANDs;
- y witness: `artifacts/post190_nist_variants_wide/y_candidate_0.json`, 13 ANDs;
- total: 27 fixed AND nodes.

Both witnesses reproduce their three target functions on all 64 side inputs.
The joint audit remaps x inputs to symbols 0–5, y inputs to 6–11, x ANDs to
12–25, and y ANDs to 26–38. It then verifies dependency legality and searches
for a capacity-constrained precedence schedule.

## Nonlinear schedule

With capacity six RCCXs per batch, the exact bounded scheduler found five
batches:

```text
B1: x0, x1, x5, y0, y2, y5
B2: y6, x2, x3, x6, x7, x10
B3: x8, x11, y1, y7, y8, y10
B4: x12, y3, y9, y11, x4, x9
B5: x13, y4, y12
```

The printed zero-based node indices in `report.json` are authoritative; the
human names above are a compact interpretation of the combined ordering.
Because `ceil(27/6)=5`, this reaches the absolute capacity lower bound. At the
logical RCCX estimate of seven native layers per batch, forward nonlinear
depth is 35 layers.

The audit was also repeated over the retained portfolio: four x14 candidates
times eight y13 candidates, for 32 exact witness pairs. Every pair admits a
five-batch capacity schedule, so candidate-0 × candidate-0 is not being used
as a proxy for the entire x14+y13 family.

## Depth budget

The preserved kernel estimate used by the proposal is about 38 native layers.
To reach a 137-depth complete oracle, the forward encoder target is therefore
at most 49 layers:

```text
2 * D_encoder + 38 <= 137  =>  D_encoder <= 49
```

The five nonlinear batches consume approximately 35 layers, leaving only 14
layers for all affine frame preparation, routing, output placement, and any
boundary overhead. This is a viability target, not a result.

## What this run did and did not prove

Implemented in `src/post190_joint_18wire_feasibility.py`:

- exact loading and validation of the fixed x14/y13 witnesses;
- exact all-64-input Boolean checks for both sides;
- one joint symbol-space remapping;
- exact bounded backtracking for a five-batch, six-RCCX-capacity schedule;
- complete enumeration of the retained 4×8 witness-pair portfolio for that
  capacity screen;
- derivation of the 35-layer nonlinear estimate and 14-layer affine budget.

Not implemented by this pre-screen:

- the requested SAT model of 18 physical wire rows;
- actual CNOT-layer disjointness and affine-depth binary search;
- native construction of `E K E†`;
- QASM serialization or exhaustive 4096-input verification.

Consequently this is neither an UNSAT certificate nor a candidate oracle. It
only confirms that the fixed Boolean witness pair is not rejected by the most
basic joint nonlinear-capacity test. The next exact step, if pursued, is the
symbolic affine-frame SAT model with variable batch assignments, starting at
A=14 and then probing A=15…18 if A=14 is UNSAT. It should use actual CNOT
matchings and literal-versus-span endpoint modes, with an external process
bound via `src/run_bounded.py`.

## Free-frame diagnostic follow-up

`src/post190_joint_18wire_freeframe_sat.py` records a semantic endpoint
diagnostic using actual 4096-point functions. It confirms that the eight
requested endpoint functions are distinct and lie in the affine span of the
full set of generated functions. It also demonstrates why that is not yet a
free-frame SAT model: the full symbolic function set has rank 40, while only 18
physical rows exist. A valid dirty computation may replace old row directions,
so the solver must model row replacement and future-use preservation rather
than simply accumulating every node in one span.

Accordingly its status is deliberately named
`RELAXED_ENDPOINT_PASS_STORAGE_UNMODELED`, not `FREEFRAME_SAT`. No UNSAT or
SAT conclusion about the 18-wire architecture is drawn from it.

## First storage-aware free-frame result

**Superseded correctness warning (September16):** the original0.13-second
UNSAT below was produced by a defective model and must not be used as evidence.
See the corrected follow-up after this historical paragraph.

`src/post190_joint_18wire_storage_sat.py` implements the next, stricter model
for candidate-0 and the first recorded five-batch schedule. It uses 40-bit
semantic coordinates, six explicit invertible 18×18 affine frames, canonical
mutually disjoint RCCX placements, dirty-target updates, and literal endpoint
descriptor rows. The solver returned **UNSAT in 0.13 seconds** with a 30-second
solver bound.

This is only a fixed-schedule result. It does not reject the other legal
five-batch placements, the other 31 witness pairs, or a native CNOT-depth
realization. The next valid expansion is to test alternative batch schedules
and then the remaining witness portfolio; only an exhaustive UNSAT over those
cases could close the fixed x14+y13 family.

Artifact: `artifacts/post190_joint_18wire_storage/report.json`.

## Corrected storage model and bounded portfolio probes

The v2 fix repairs six defects in `post190_joint_18wire_storage_sat.py`:

- Already-global operand indices were passed through the local side mapper again.
- The x raw endpoint omitted x5; it must be x4 XOR x5.
- The initial-row expression required j==bit and j==bit-1 simultaneously, so
  every input row was zero.
- Independent frame replay used integer sum rather than GF(2) XOR.
- Replay ignored the actual supplied schedule in favor of the module constant.
- Replay did not independently check extracted frame/inverse products.

The semantic endpoint diagnostic's x raw tag and misleading accumulated-span
comment were also corrected. Tests compare every operand product and endpoint
with actual4096-input truth tables. Formal coordinates have verified rank40 for
each probed witness pair, so the formal-symbol model is exact for that pair's
affine forms. Small known-feasible dirty and clean cases return SAT; a missing
nonlinear direction returns UNSAT. These replace the regression test that
simply asserted the old erroneous UNSAT result.

The corrected original fixed schedule returns UNSAT in0.42 seconds. A separate
campaign tests eight witness pairs (two y choices for each of four x choices)
with their saved schedules and four additional legal five-batch schedules for
the initial pair. All12 are UNSAT, with solver checks about0.32–0.38 seconds.
These results exclude those exact once-per-node batch models, with arbitrary
invertible affine frames. They do not exclude every schedule, all32 pairs,
recomputation, different Boolean networks, or a more general destructive circuit.
No CNOT-depth optimum or native encoder follows from these probes.

Artifacts: `artifacts/post190_joint_18wire_storage_v2/`,
`artifacts/post190_joint_storage_campaign_v2/`, and their external wall reports.
Both processes completed. The original artifact is preserved as invalid history.

## Reproduction

From the workspace root:

```sh
PYTHONPATH=src .venv/bin/python src/post190_joint_18wire_feasibility.py
```

Output: `artifacts/post190_joint_18wire_feasibility/report.json`.

No protected package was modified. In particular, `artifacts/185/` remains the
current protected best under the current handoff.
