# Native v2 encoder checkpoint — September 12, 2026

The requested bounded experiment was implemented. It did **not** meet the
roughly 31-depth encoder checkpoint. The best constructed encoder is **301
U3/CX depth / 176 CX / 9 qubits**, and is numerically verified on all 64 input
coordinates. This is an encoder result, not a complete phase oracle or a new
repository best. The verified 456-depth oracle remains unchanged.

## Construction and search scope

`src/v2_native_checkpoint.py` enumerates codebooks in which two level classes
may each use two codewords and the remaining four classes each use one. For
six classes and eight codewords these occupy the entire code space. An output
affine normalization fixes three singleton codes to 0, 1, 2; the remaining
singleton and paired code assignments are enumerated.

Within each codebook, the selected codeword at each input depends on one
Boolean selector. Bounds on ANF degree become linear constraints on those
selectors. The completed degree-5 run produced 1,248 assignments using eight
structured free-selector choices per feasible codebook. It then chose output
linear frames by a per-output primitive-depth proxy and compiled the six best
retained table triples with three schedules each: **18 native candidates**.
This is not an exhaustive search of all degree-5 functions or native circuits.

The lowering uses mixed-polarity ESOP toggles, RCCX, RC3X, and full dirty-helper
MCX decompositions with relative phases. All six coordinate bits are preserved
by the encoder. Other output wires can be borrowed as dirty scratch and must
be restored by each primitive. There is no assumption that dirty helpers start
at zero, and every Qiskit transpilation explicitly disables that assumption.
No action-only MCX fragment is used.

This particular lowering still pays for high-control terms and does not share
nonlinear products across them. The best proxy was 134 on an output wire, but
actual native scheduling across shared controls and helper wires yielded 301.
Even the proxy was already above the agreed checkpoint. A destructive,
product-factored encoder was not constructed; the result cannot exclude one.

The earlier degree-4 SAT pilot (`artifacts/v2_degree4_codes.json`) produced no
code within its five-second per-case limits. Several cases timed out, so its
overall status is unresolved, not UNSAT. The direct paired-code construction
also produced no degree-4 candidate; this does not cover a single class using
three codewords and is not a general degree-4 exclusion.

## Verified artifact

- QASM: `artifacts/v2_native_checkpoint/encoder.qasm`
- Verification: `artifacts/v2_native_checkpoint/encoder.verification.json`
- Full candidate metrics, truth tables, and replay seed:
  `artifacts/v2_native_checkpoint/report.json`
- SHA-256:
  `2ae8fa8fb7d02e60ffd56b3e6f40fe4953dfb56315c1a7e03609c7c6938b54a7`
- Output code sets by level 0 through 5:
  `{0}`, `{5,6}`, `{2}`, `{3}`, `{1,7}`, `{4}`.

The verifier parses the serialized nine-qubit U3/CX QASM and checks its 64
clean-ancilla input columns, including preservation of all six coordinate bits
and absence of off-target amplitudes. Input-dependent encoder phases are
allowed. Maximum column error is 1.89e-15.

It also checks `E† Z(mask) E` for all seven nonempty code-parity masks, including
restoration of the input and all three ancillas. Maximum sandwich error is
3.78e-15. All local relative-phase primitives are independently checked on
every basis input, including all dirty-helper assignments. Their monomial
behavior justifies phase cancellation around an arbitrary intervening diagonal
code operation.

`src/exhaustive_verify.py` is the complete 12-input logo-oracle verifier, so it
is not applicable to this nine-qubit encoder. No full oracle candidate was
promoted or claimed. An eventual integrated new best would still require that
verifier on its exact standalone QASM.

## Reproduction and tests

```sh
.venv/bin/python src/v2_native_checkpoint.py --seconds 35 --outdir artifacts/v2_native_checkpoint_new
.venv/bin/python src/v2_native_checkpoint.py --replay artifacts/v2_native_checkpoint/report.json --outdir /tmp/classiq_v2_replay_new
.venv/bin/python -m pytest -q tests/test_v2_native_checkpoint.py tests/test_level_split_code_screen.py
```

Six focused tests pass. The saved report replay was also run and reproduced
the exact QASM SHA. The output directory must be new: existing QASM files are
not overwritten. The default degree-3 behavior of the earlier split-code
screen is retained; it now also accepts an explicit `--degree` parameter.

## Decision

Do not integrate this encoder, synthesize the other three encoders using this
lowering, or run more scheduling seeds. It is worse than the existing
multiplexer encoder and misses the target by a large margin. This closes the
implemented split-code/ESOP lowering checkpoint, not the general v2 encoder
problem. Sub-180 remains unfinished.
