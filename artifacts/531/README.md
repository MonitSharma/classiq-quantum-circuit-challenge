# Depth-531 package

This folder contains the current best locally verified standalone oracle:

- `full_mux_531.qasm`: exact `u3`/`cx` QASM, 18 qubits, depth 531, 1,020 CX.
- `full_mux_531.exhaustive.json`: verification report for that exact file.
- `full_mux_531.qmod`: Classiq-level logical `qperm` model for the same logo phase oracle.

The QASM SHA-256 is
`8f7e2617cf1435ea76cc70688544b4b0e3a8b5082d82293f98777d90d5a3fda6`.

The QASM was derived from `artifacts/full_mux.qasm` (seed 94, depth 536) by
pytket `FullPeepholeOptimise` followed by exact `u3`/`cx` rebasing. The QMOD
describes the logical oracle and is suitable as a Classiq submission model;
it is not expected to synthesize back to the identical optimized QASM.
