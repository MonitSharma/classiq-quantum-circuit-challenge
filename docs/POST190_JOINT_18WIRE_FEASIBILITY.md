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

## Reproduction

From the workspace root:

```sh
PYTHONPATH=src .venv/bin/python src/post190_joint_18wire_feasibility.py
```

Output: `artifacts/post190_joint_18wire_feasibility/report.json`.

No protected package was modified. In particular, `artifacts/185/` remains the
current protected best under the current handoff.
