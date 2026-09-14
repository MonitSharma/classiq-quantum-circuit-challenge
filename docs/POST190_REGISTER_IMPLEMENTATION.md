# Register-aware implementation and bounded experiments

Implemented the proposed work. The verified logo best remains **190/857/18**;
no protected-label encoder improvement was found in these bounded runs.

## Actual register-state search for XAG witnesses

`src/post190_xag_register_schedule.py` tracks the GF(2) span of the named AND
signals held across THREE ancillas. Six primary inputs stay available. A node
can be computed, accumulated, or erased only if both operands are obtainable
without the target wire. Reversible ancilla basis changes are allowed. It does
not pretend that a dirty register holds a clean node or that sink status alone
establishes lowerability.

BFS searches the finite space of at-most-three-dimensional subspaces, minimizing
nonlinear toggles with affine basis changes treated as free at this search stage.
The resulting circuit is then actually compiled and measured: toggle optimality
is not native-depth optimality. Exhaustion applies only to this named-signal,
input-preserving lowering model; it does not exclude overwriting coordinate
wires, other Boolean factorizations, or other quantum constructions.

The implementation uses GF(2) rank, exact output reconstruction, and in-place
affine controls. Its RCCX phases are permitted because the complete encoder is
paired with its actual inverse around the diagonal phase operation.

Tests and measured constructions:

* Supplied synthetic k=3 example: schedule found and quantum verified.
* A constructed k=7 example with FOUR internal nodes and three sinks:
  **eight nonlinear toggles, nine wires**, encoder **75 depth / 51 CX**.
  All 64 arbitrary primary-input basis states pass through the encoder and
  complete synthetic phase/uncompute circuit, error 1.07e-15. The full synthetic
  phase circuit is depth137. These are NOT logo metrics or protected labels.
  Files: `artifacts/post190_register_schedule_four_internal/optimized/`.
* A different shallow k=7 example with high-degree outputs: the restricted
  model exhausts 766 states without a schedule. No general impossibility claim.
  Files: `artifacts/post190_register_schedule_toy7/result/`.

Run a protected-label witness through the complete pipeline with:

```
.venv/bin/python src/post190_xag_register_schedule.py \
  --witness /absolute/path/to/witness.json --side y --outdir artifacts/NEW_NAME
```

`--side` first checks all target functions, then (if a schedule exists) composes
the lowered encoder with the protected kernel and the other existing encoder,
and exhaustively verifies the serialized full oracle. The x-side raw parity
is explicitly exposed before composition. Omitting `--side` supports synthetic
compiler tests but does not claim the witness is a logo encoder.

## Direct nine-wire reversible search

`src/post190_register_encoder.py` models the actual truth vector on every wire
through reversible X/CX/Toffoli operations. Only three ancillas start zero.
It prescribes the three code outputs and retained raw tag; the remaining five
wires can hold garbage, which the actual inverse later restores.

The tested templates use four or six layers of up to three disjoint RCCX gates,
two disjoint-CX layers before/between/after those layers, and initial/final X
layers. Explicit native decomposition gives conditional encoder budgets of 48
and 70 layers. Those are template budgets, NOT synthesized protected encoders.

With 15 seconds per solver call:

| instance | result |
|---|---|
| y, 48-layer template, all64 inputs | UNKNOWN/timeout |
| x, 48-layer template, all64 inputs | UNKNOWN/timeout |
| y, 48-layer template, 8 samples | UNKNOWN/timeout |
| x, 48-layer template, 8 samples | SAT, fails 47 full inputs; rejected |
| x, same template, 16 samples after counterexamples | UNKNOWN/timeout |
| y, 70-layer template, 16 samples | UNKNOWN/timeout |
| x, 70-layer template, 16 samples | UNKNOWN/timeout |

Reports are under `artifacts/post190_register_{x,y}_*`. A nonlinear positive
control solves and passes all64 quantum checks. No partial-sample witness was
promoted to an encoder or submission. A future full witness is automatically
composed and exhaustively verified, not just assigned an AND-count score.

## Full composition and preservation

`src/post190_register_compose.py` validates replacement nine-wire encoders,
retains the saved kernel and its physical ancilla permutation, and uses the
actual encoder inverse with the corresponding wire mapping. It accepts one
or both replacements and scores the serialized complete oracle.

The no-replacement replay reproduces the protected QASM byte-for-byte:
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.
All4096 inputs pass, maximum error7.78e-15, zero ancilla error, 190/857/18.
Report: `artifacts/post190_register_compose_baseline/oracle.exhaustive.json`.

Four focused tests pass in `tests/test_post190_register_schedule.py` and
`tests/test_post190_register_encoder.py`. Every transpilation uses the safe
native helper with initially-zero assumptions disabled and output layouts
materialized. Original notebook and protected submission files are untouched.

All runs launched for this implementation finished. Previously running external
searches were not modified or claimed to be alive; process inspection is blocked
in this environment. No monitoring or background continuation was scheduled.

The next useful input is a real protected-label witness or a successful direct
register circuit. The compiler/storage question is now executable instead of
being inferred from a retirement flag; the target native-depth improvement
remains unresolved.
