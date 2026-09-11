# MPO-native synthesis campaign

## Status

This campaign is on branch `mpo-native-synthesis`. It optimizes the target
diagonal unitary directly rather than computing `logo(x,y)` into a classical
workspace. No submitted or verified competition circuit has been produced
yet. The protected `artifacts/524/full_mux_feature_linear_tket_524.qasm` file
is unchanged.

## Structural reproduction

The first milestone is implemented in `src/mpo_target.py`. It constructs the
sign tensor directly from `src/search.py::logo`, using the explicit tensor-axis
order

```text
q0, q1, q2, q3, q4, q5, q11, q8, q6, q7, q9, q10
```

The reproducible command is:

```sh
.venv/bin/python src/mpo_target.py
```

The current deterministic report is
`artifacts/mpo_native/structural_report.json`. It records:

| Quantity | Result |
|---|---:|
| Marked states | 1097 / 4096 |
| Sign-table SHA-256 | `9013c7bf82abcb1cbbcfff367b7321fb02c2a1cc1ba26ab2051640fd9b0eba13` |
| TT ranks, including endpoints | `[1, 2, 4, 8, 11, 12, 11, 12, 13, 8, 4, 2, 1]` |
| Maximum TT rank | 13 |
| Maximum TT reconstruction error | `2.01e-13` |
| Maximum diagonal-MPO basis-action error | `2.01e-13` |

The decomposition is saved as `artifacts/mpo_native/target_tt.npz`; the
diagonal MPO cores are saved separately as
`artifacts/mpo_native/target_mpo.npz`. The sign table is saved as
`artifacts/mpo_native/target_signs.npy`.

The TT ranks are numerical ranks from double-precision SVD with a relative
cutoff of `1e-12`. Reconstruction is checked over every tensor entry, and the
MPO action is checked over every 12-bit basis string. This establishes the
claimed tensor structure, but it does not establish a shallow circuit: MPO
bond dimension is not a depth bound, and TT cores are not automatically
unitary or isometric.

## Planned synthesis experiments

The next bounded experiment should optimize a full-operator objective for
12-qubit circuits with no ancillas. Candidate circuits must be evaluated as
operators, not by state fidelity or diagonal entries alone. The process
fidelity target is

```text
|Tr(U_target† V)|² / 4096²
```

The initial topology ladder should include TT-order matchings, all-to-all
round-robin matchings, and explicit x-y matchings at 4, 6, 8, 10, 12, 16,
20, and 24 parallel two-qubit layers. Every promising result must eventually
be decomposed to exact `u3`/`cx` QASM and checked with the repository's
exhaustive verifier and dense random-state verifier. No abstract SU(4) depth
or optimizer loss will be treated as a competition result.

The optimizer must also preserve arbitrary input states. Any future use of
Qiskit transpilation for reusable circuit pieces must pass
`qubits_initially_zero=False`, consistent with the repository-wide correctness
rule.

